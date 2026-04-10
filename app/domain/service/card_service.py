from __future__ import annotations

from collections.abc import Iterable
from app.integration.card_integration import HttpCardIntegration
from app.domain.models.card.card_data import CardData


class CardService:
    def __init__(self, card_integration: HttpCardIntegration) -> None:
        self._card_integration = card_integration

    async def fetch_cards(self, card_names: Iterable[str]) -> list[CardData]:
        return await self._card_integration.fetch_cards(card_names)
