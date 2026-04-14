from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable
from typing import Any

import httpx

from app.domain.models.card.card_data import CardData
from app.domain.models.deck.deck_entry import DeckEntry

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
    def __init__(self, message: str, missing_names: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing_names = missing_names or []


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

    async def fetch_cards_by_entries(self, entries: Iterable[DeckEntry]) -> list[CardData]:
        normalized_entries = self._normalize_entries(entries)
        if not normalized_entries:
            return []

        timeout = httpx.Timeout(20.0)
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        async with httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            headers=DEFAULT_HEADERS,
        ) as client:
            all_cards: list[CardData] = []
            total_batches = (len(normalized_entries) + SCRYFALL_BATCH_SIZE - 1) // SCRYFALL_BATCH_SIZE
            missing_entries: list[str] = []

            for batch_index, batch_names in enumerate(
                self._chunked(normalized_entries, SCRYFALL_BATCH_SIZE),
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
                missing_entries.extend(batch_missing_names)

        if missing_entries:
            raise CardEnrichmentError(f"Cards not found: {missing_entries}", missing_names=missing_entries)

        return all_cards

    async def _fetch_collection_batch(
        self,
        entries: list[DeckEntry],
        client: httpx.AsyncClient,
    ) -> tuple[list[CardData], list[str]]:
        payload = {
            "identifiers": [self._build_identifier(entry) for entry in entries],
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
            alias_map: dict[str, CardData] = {}
            exact_map: dict[tuple[str, str, str], CardData] = {}
            for item in payload.get("data") or []:
                card = self._build_card_data_from_scryfall(item)
                name = item.get("name")
                set_code = item.get("set")
                collector_number = item.get("collector_number")
                if name and set_code and collector_number:
                    exact_map[
                        (
                            str(name).casefold(),
                            str(set_code).upper(),
                            str(collector_number),
                        )
                    ] = card
                for alias in self._extract_card_aliases(item):
                    alias_map.setdefault(alias.casefold(), card)

            missing_names = [
                self._identifier_label_from_payload_item(item)
                for item in payload.get("not_found") or []
                if self._identifier_label_from_payload_item(item)
            ]
            cards: list[CardData] = []
            for requested_entry in entries:
                card = None
                if requested_entry.set_code and requested_entry.collector_number:
                    card = exact_map.get(
                        (
                            requested_entry.card_name.casefold(),
                            requested_entry.set_code.upper(),
                            requested_entry.collector_number,
                        )
                    )
                if card is None:
                    card = alias_map.get(requested_entry.card_name.casefold())
                if card:
                    cards.append(card)
                    continue
                requested_label = self._entry_label(requested_entry)
                if requested_label not in missing_names:
                    missing_names.append(requested_label)

            return cards, missing_names

        raise ScryfallRateLimitExceeded()

    @staticmethod
    def _normalize_entries(entries: Iterable[DeckEntry]) -> list[DeckEntry]:
        seen: set[tuple[str, str | None, str | None]] = set()
        normalized_entries: list[DeckEntry] = []
        for entry in entries:
            normalized_name = str(entry.card_name).strip()
            if not normalized_name:
                continue
            normalized_set = (entry.set_code or "").strip().upper() or None
            normalized_collector = (entry.collector_number or "").strip() or None
            key = (normalized_name.casefold(), normalized_set, normalized_collector)
            if key in seen:
                continue
            seen.add(key)
            normalized_entries.append(
                entry.model_copy(
                    update={
                        "card_name": normalized_name,
                        "set_code": normalized_set,
                        "collector_number": normalized_collector,
                    }
                )
            )
        return normalized_entries

    @staticmethod
    def _chunked(items: list[DeckEntry], size: int) -> list[list[DeckEntry]]:
        return [items[index:index + size] for index in range(0, len(items), size)]

    @staticmethod
    def _build_identifier(entry: DeckEntry) -> dict[str, str]:
        if entry.set_code and entry.collector_number:
            return {
                "set": entry.set_code.lower(),
                "collector_number": entry.collector_number,
            }
        return {"name": entry.card_name}

    @staticmethod
    def _entry_label(entry: DeckEntry) -> str:
        if entry.set_code and entry.collector_number:
            return f"{entry.card_name} ({entry.set_code}) {entry.collector_number}"
        if entry.collector_number:
            return f"{entry.card_name} (#{entry.collector_number})"
        return entry.card_name

    @classmethod
    def _identifier_label_from_payload_item(cls, item: dict[str, Any]) -> str | None:
        name = item.get("name")
        set_code = item.get("set")
        collector_number = item.get("collector_number")
        if name and set_code and collector_number:
            return f"{name} ({str(set_code).upper()}) {collector_number}"
        if name:
            return str(name)
        if set_code and collector_number:
            return f"({str(set_code).upper()}) {collector_number}"
        return None

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

    @staticmethod
    def _extract_card_aliases(data: dict[str, Any]) -> list[str]:
        aliases: list[str] = []
        name = data.get("name")
        if name:
            aliases.append(str(name))

        for card_face in data.get("card_faces") or []:
            face_name = card_face.get("name")
            if face_name:
                aliases.append(str(face_name))

        return aliases
