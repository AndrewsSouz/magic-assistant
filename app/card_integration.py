from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Iterable, List
import httpx

from app.models import CardData

log = logging.getLogger(__name__)

SCRYFALL_NAMED_URL = "https://api.scryfall.com/cards/named"
MTG_API_CARDS_URL = "https://api.magicthegathering.io/v1/cards"
DEFAULT_HEADERS = {
    "User-Agent": "magic-assistant-mvp/0.1.0",
    "Accept": "application/json;q=0.9,*/*;q=0.8",
}
SCRYFALL_MIN_INTERVAL_SECONDS = 2.5
SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS = 5.0
MAX_SCRYFALL_FALLBACK_CARDS = 10


class CardLookupError(Exception):
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
            self._next_request_at = max(self._next_request_at, time.monotonic() + self.min_interval_seconds)

            cooldown_seconds = None
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    cooldown_seconds = float(retry_after) if retry_after is not None else SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS
                except ValueError:
                    cooldown_seconds = SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS

                self._blocked_until = max(self._blocked_until, time.monotonic() + cooldown_seconds)

            return response, cooldown_seconds


SCRYFALL_RATE_LIMITER = ScryfallRateLimiter(SCRYFALL_MIN_INTERVAL_SECONDS)


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


def _build_card_data_from_mtg_api(data: dict[str, Any]) -> CardData:
    legalities = {}
    for item in data.get("legalities") or []:
        format_name = item.get("format")
        legality = item.get("legality")
        if format_name and legality:
            legalities[format_name] = legality

    return CardData(
        name=data.get("name"),
        mana_cost=data.get("manaCost"),
        cmc=data.get("cmc"),
        type_line=data.get("type"),
        oracle_text=data.get("text"),
        colors=data.get("colors", []),
        color_identity=data.get("colorIdentity", []),
        legalities=legalities,
        image_url=data.get("imageUrl"),
        scryfall_uri=None,
    )


async def _fetch_scryfall_named(
    card_name: str,
    lookup_type: str,
    client: httpx.AsyncClient,
) -> CardData | None:
    for attempt in range(2):
        response, cooldown_seconds = await SCRYFALL_RATE_LIMITER.execute(
            lambda: client.get(SCRYFALL_NAMED_URL, params={lookup_type: card_name})
        )

        if response.status_code == 429:
            log.warning(
                "Scryfall %s lookup for '%s' hit 429; cooling down for %.2f seconds",
                lookup_type,
                card_name,
                cooldown_seconds or SCRYFALL_DEFAULT_COOLDOWN_AFTER_429_SECONDS,
            )
            if attempt == 0:
                continue
            raise ScryfallRateLimitExceeded()

        if response.status_code >= 400:
            log.warning("Scryfall %s lookup for '%s' failed with status %s", lookup_type, card_name, response.status_code)
            return None

        return _build_card_data_from_scryfall(response.json())

    return None


async def _fetch_from_mtg_api(card_name: str, client: httpx.AsyncClient) -> CardData | None:
    response = await client.get(MTG_API_CARDS_URL, params={"name": f'"{card_name}"'})
    if response.status_code >= 400:
        log.warning("MTG API lookup for '%s' failed with status %s", card_name, response.status_code)
        return None

    cards = (response.json() or {}).get("cards") or []
    if not cards:
        log.warning("MTG API lookup for '%s' returned no results", card_name)
        return None

    exact_match = next(
        (card for card in cards if (card.get("name") or "").casefold() == card_name.casefold()),
        None,
    )
    selected_card = exact_match or cards[0]
    return _build_card_data_from_mtg_api(selected_card)


async def fetch_card_by_name(card_name: str, client: httpx.AsyncClient) -> CardData:
    card = await _fetch_from_mtg_api(card_name, client)
    if card:
        return card

    try:
        card = await _fetch_scryfall_named(card_name, "exact", client)
    except ScryfallRateLimitExceeded:
        card = None
    if card:
        return card

    try:
        card = await _fetch_scryfall_named(card_name, "fuzzy", client)
    except ScryfallRateLimitExceeded:
        card = None
    if card:
        return card

    log.warning("Could not resolve '%s' in Scryfall or MTG API; returning minimal card data", card_name)
    return CardData(name=card_name)


async def fetch_cards(card_names: Iterable[str]) -> List[CardData]:
    card_names = list(card_names)
    timeout = httpx.Timeout(20.0)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    async with httpx.AsyncClient(timeout=timeout, limits=limits, headers=DEFAULT_HEADERS) as client:
        mtg_tasks = [_fetch_from_mtg_api(name, client) for name in card_names]
        mtg_results = await asyncio.gather(*mtg_tasks)

        cards: List[CardData] = []
        missing_names: List[str] = []
        missing_indexes: List[int] = []

        for index, (name, mtg_card) in enumerate(zip(card_names, mtg_results)):
            if mtg_card:
                cards.append(mtg_card)
                continue

            cards.append(CardData(name=name))
            missing_names.append(name)
            missing_indexes.append(index)

        if not missing_names:
            return cards

        if len(missing_names) > MAX_SCRYFALL_FALLBACK_CARDS:
            log.warning(
                "Skipping Scryfall fallback for %s card(s); limit is %s. Returning minimal card data for misses.",
                len(missing_names),
                MAX_SCRYFALL_FALLBACK_CARDS,
            )
            return cards

        log.warning("Trying Scryfall fallback for %s unresolved card(s)", len(missing_names))
        for index, name in zip(missing_indexes, missing_names):
            try:
                scryfall_card = await _fetch_scryfall_named(name, "exact", client)
                if not scryfall_card:
                    scryfall_card = await _fetch_scryfall_named(name, "fuzzy", client)
            except ScryfallRateLimitExceeded:
                scryfall_card = None

            if scryfall_card:
                cards[index] = scryfall_card
            else:
                log.warning("Returning minimal card data for '%s' after fallback attempts", name)

        return cards
