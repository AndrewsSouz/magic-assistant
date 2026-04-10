from __future__ import annotations

from functools import lru_cache

from app.domain.service.card_service import CardService
from app.domain.service.deck_service import DeckService
from app.domain.service.llm_analysis_service import LlmAnalysisService
from app.integration.card_integration import HttpCardIntegration
from app.integration.llm_integration import LlmIntegration


@lru_cache
def get_card_integration() -> HttpCardIntegration:
    return HttpCardIntegration()


@lru_cache
def get_llm_integration() -> LlmIntegration:
    return LlmIntegration()


def get_card_service() -> CardService:
    return CardService(get_card_integration())


def get_llm_analysis_service() -> LlmAnalysisService:
    return LlmAnalysisService(get_llm_integration())


def get_deck_service() -> DeckService:
    return DeckService(
        card_service=get_card_service(),
        llm_analysis_service=get_llm_analysis_service(),
    )
