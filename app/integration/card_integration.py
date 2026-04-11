from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable
from typing import Any

import httpx

from app.domain.models.card.card_data import CardData

log = logging.getLogger(__name__)

SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
SCRYFALL_BATCH_SIZE = 75
DEFAULT_HEADERS = {
    "User-Agent": "magic-assistant-mvp/0.1.0",
    "Accept": "application/json;q=0.9,*/*;q=0.8",
}
SCRYFALL_MIN_INTERVAL_SECONDS = 0.15
SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS = 3.0


class CardEnrichmentError(Exception):
    pass


class ScryfallRateLimitExceeded(Exception):
    pass


class ScryfallRateLimiter:
    def __init__(self, min_interval_seconds: float) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._lock = asyncio.Lock()
        self._next_request_at = 0.0
        self._blocked_until = 0.0

    async def execute(self, request_coro) -> tuple[httpx.Response, float | None]:
        async with self._lock:
            while True:
                now = time.monotonic()
                wait_time = max(self._next_request_at - now, self._blocked_until - now, 0.0)
                if wait_time <= 0:
                    break
                await asyncio.sleep(wait_time)

            response = await request_coro()
            self._next_request_at = max(
                self._next_request_at,
                time.monotonic() + self.min_interval_seconds,
            )

            cooldown_seconds = None
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    cooldown_seconds = (
                        float(retry_after)
                        if retry_after is not None
                        else SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS
                    )
                except ValueError:
                    cooldown_seconds = SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS

                self._blocked_until = max(
                    self._blocked_until,
                    time.monotonic() + cooldown_seconds,
                )

            return response, cooldown_seconds


class HttpCardIntegration:
    def __init__(self) -> None:
        self._scryfall_rate_limiter = ScryfallRateLimiter(SCRYFALL_MIN_INTERVAL_SECONDS)

    async def fetch_cards_by_exact_names(self, card_names: Iterable[str]) -> list[CardData]:
        normalized_names = self._normalize_card_names(card_names)
        if not normalized_names:
            return []

        timeout = httpx.Timeout(20.0)
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            headers=DEFAULT_HEADERS,
        ) as client:
            all_cards: list[CardData] = []
            total_batches = (len(normalized_names) + SCRYFALL_BATCH_SIZE - 1) // SCRYFALL_BATCH_SIZE
            missing_names: list[str] = []

            for batch_index, batch_names in enumerate(
                self._chunked(normalized_names, SCRYFALL_BATCH_SIZE),
                start=1,
            ):
                log.info(
                    "Sending batch %s/%s to Scryfall collection with %s unique card(s)",
                    batch_index,
                    total_batches,
                    len(batch_names),
                )
                batch_cards, batch_missing_names = await self._fetch_collection_batch(batch_names, client)
                all_cards.extend(batch_cards)
                missing_names.extend(batch_missing_names)

        if missing_names:
            raise CardEnrichmentError(f"Cards not found: {missing_names}")

        return all_cards

    async def _fetch_collection_batch(
        self,
        card_names: list[str],
        client: httpx.AsyncClient,
    ) -> tuple[list[CardData], list[str]]:
        payload = {
            "identifiers": [{"name": card_name} for card_name in card_names],
        }

        for attempt in range(2):
            try:
                response, cooldown_seconds = await self._scryfall_rate_limiter.execute(
                    lambda: client.post(SCRYFALL_COLLECTION_URL, json=payload)
                )
            except httpx.HTTPError as exc:
                raise CardEnrichmentError(f"Scryfall collection request failed: {exc}") from exc

            if response.status_code == 429:
                log.warning(
                    "Scryfall collection batch hit 429; cooling down for %.2f seconds",
                    cooldown_seconds or SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS,
                )
                if attempt == 0:
                    continue
                raise ScryfallRateLimitExceeded()

            if response.status_code >= 400:
                raise CardEnrichmentError(
                    f"Scryfall collection batch failed with status {response.status_code}"
                )

            payload = response.json() or {}
            cards = [
                self._build_card_data_from_scryfall(item)
                for item in payload.get("data") or []
            ]
            missing_names = [
                str(item.get("name"))
                for item in payload.get("not_found") or []
                if item.get("name")
            ]

            found_names = {card.name.casefold(): card for card in cards}
            for requested_name in card_names:
                if requested_name.casefold() not in found_names and requested_name not in missing_names:
                    missing_names.append(requested_name)

            return cards, missing_names

        raise ScryfallRateLimitExceeded()

    @staticmethod
    def _normalize_card_names(card_names: Iterable[str]) -> list[str]:
        seen: set[str] = set()
        normalized_names: list[str] = []
        for card_name in card_names:
            normalized_name = str(card_name).strip()
            if not normalized_name:
                continue
            key = normalized_name.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized_names.append(normalized_name)
        return normalized_names

    @staticmethod
    def _chunked(items: list[str], size: int) -> list[list[str]]:
        return [items[index:index + size] for index in range(0, len(items), size)]

    @staticmethod
    def _build_card_data_from_scryfall(data: dict[str, Any]) -> CardData:
        image_uris = data.get("image_uris") or {}
        card_faces = data.get("card_faces") or []
        face_image = None
        if not image_uris and card_faces:
            first_face = card_faces[0] or {}
            face_image = (first_face.get("image_uris") or {}).get("normal")

        return CardData(
            name=data.get("name"),
            mana_cost=data.get("mana_cost"),
            cmc=data.get("cmc"),
            type_line=data.get("type_line"),
            oracle_text=data.get("oracle_text"),
            colors=data.get("colors", []),
            color_identity=data.get("color_identity", []),
            legalities=data.get("legalities", {}),
            image_url=image_uris.get("normal") or face_image,
            scryfall_uri=data.get("scryfall_uri"),
        )
