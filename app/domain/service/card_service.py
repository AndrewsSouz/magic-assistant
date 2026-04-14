from __future__ import annotations

from collections.abc import Iterable

from app.domain.models.card.card_data import CardData
from app.domain.models.deck.deck_entry import DeckEntry
from app.integration.card_integration import HttpCardIntegration


class CardService:
    def __init__(self, card_integration: HttpCardIntegration) -> None:
        self._card_integration = card_integration

    async def fetch_cards_by_entries(self, entries: Iterable[DeckEntry]) -> list[CardData]:
        return await self._card_integration.fetch_cards_by_entries(entries)
