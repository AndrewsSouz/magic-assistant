from __future__ import annotations

import asyncio
from typing import Iterable, List
import httpx

from app.models import CardData

SCRYFALL_NAMED_URL = "https://api.scryfall.com/cards/named"


class CardLookupError(Exception):
    pass


async def fetch_card_by_name(card_name: str, client: httpx.AsyncClient) -> CardData:
    response = await client.get(SCRYFALL_NAMED_URL, params={"fuzzy": card_name})
    if response.status_code >= 400:
        raise CardLookupError(f"Could not find card '{card_name}' in Scryfall.")

    data = response.json()
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


async def fetch_cards(card_names: Iterable[str]) -> List[CardData]:
    timeout = httpx.Timeout(20.0)
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        tasks = [fetch_card_by_name(name, client) for name in card_names]
        return await asyncio.gather(*tasks)
