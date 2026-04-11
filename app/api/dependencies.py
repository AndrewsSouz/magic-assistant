from __future__ import annotations

from functools import lru_cache

from app.domain.service.auth_service import AuthService
from app.domain.service.card_service import CardService
from app.domain.service.deck_service import DeckService
from app.domain.service.llm_analysis_service import LlmAnalysisService
from app.domain.service.user_deck_service import UserDeckService
from app.integration.card_integration import HttpCardIntegration
from app.integration.deck_repository import DeckRepository
from app.integration.llm_integration import LlmIntegration
from app.integration.mongo_integration import MongoIntegration
from app.integration.user_repository import UserRepository


@lru_cache
def get_card_integration() -> HttpCardIntegration:
    return HttpCardIntegration()


@lru_cache
def get_mongo_integration() -> MongoIntegration:
    return MongoIntegration()


@lru_cache
def get_llm_integration() -> LlmIntegration:
    return LlmIntegration()


@lru_cache
def get_user_repository() -> UserRepository:
    return UserRepository(get_mongo_integration())


@lru_cache
def get_deck_repository() -> DeckRepository:
    return DeckRepository(get_mongo_integration())


def get_card_service() -> CardService:
    return CardService(get_card_integration())


def get_llm_analysis_service() -> LlmAnalysisService:
    return LlmAnalysisService(get_llm_integration())


def get_auth_service() -> AuthService:
    return AuthService(get_user_repository())


def get_user_deck_service() -> UserDeckService:
    return UserDeckService(
        user_repository=get_user_repository(),
        deck_repository=get_deck_repository(),
    )


def get_deck_service() -> DeckService:
    return DeckService(
        card_service=get_card_service(),
        llm_analysis_service=get_llm_analysis_service(),
    )
