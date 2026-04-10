from __future__ import annotations

from functools import lru_cache

from app.domain.service.card_service import CardService
from app.domain.service.deck_service import DeckService
from app.integration.card_integration import HttpCardIntegration


@lru_cache
def get_card_integration() -> HttpCardIntegration:
    return HttpCardIntegration()


def get_card_service() -> CardService:
    return CardService(get_card_integration())


def get_deck_service() -> DeckService:
    return DeckService(get_card_service())
