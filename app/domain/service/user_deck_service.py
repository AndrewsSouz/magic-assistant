from __future__ import annotations

from app.contract.models.analyze_deck_response import AnalyzeDeckResponse
from app.domain.service.analise_service import build_basic_analysis, guess_format
from app.domain.service.card_service import CardService
from app.domain.service.llm_analysis_service import LlmAnalysisService
from app.domain.models.deck.user_deck import UserDeck
from app.domain.util.deck_parser import parse_decklist
from app.integration.deck_repository import DeckRepository
from app.integration.user_repository import UserRepository


class UserDeckService:
    def __init__(
        self,
        user_repository: UserRepository,
        deck_repository: DeckRepository,
        card_service: CardService,
        llm_analysis_service: LlmAnalysisService | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._deck_repository = deck_repository
        self._card_service = card_service
        self._llm_analysis_service = llm_analysis_service

    @property
    def enabled(self) -> bool:
        return self._user_repository.enabled and self._deck_repository.enabled

    async def create_deck(
        self,
        user_id: str,
        name: str,
        decklist: str,
        format_hint: str | None,
        goal: str | None,
    ) -> UserDeck:
        if not user_id.strip():
            raise ValueError("user_id é obrigatório.")
        if not name.strip():
            raise ValueError("name é obrigatório.")
        if not decklist.strip():
            raise ValueError("decklist é obrigatório.")

        user = await self._user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado.")

        parsed_deck = parse_decklist(decklist)
        if not parsed_deck.mainboard:
            raise ValueError("Decklist inválida ou vazia.")

        cards = await self._card_service.fetch_cards(
            [item.card_name for item in parsed_deck.mainboard]
        )
        resolved_format_guess = format_hint or guess_format(parsed_deck)

        deck = UserDeck(
            id="",
            user_id=user_id,
            name=name.strip(),
            decklist=decklist.strip(),
            parsed_deck=parsed_deck,
            cards=cards,
            format_guess=resolved_format_guess,
            card_count=sum(item.quantity for item in parsed_deck.mainboard),
            sideboard_count=sum(item.quantity for item in parsed_deck.sideboard),
            format_hint=format_hint,
            goal=goal,
        )
        return await self._deck_repository.create(deck)

    async def list_user_decks(self, user_id: str) -> list[UserDeck]:
        if not user_id.strip():
            raise ValueError("user_id é obrigatório.")
        return await self._deck_repository.list_by_user_id(user_id)

    async def get_user_deck(self, user_id: str, deck_id: str) -> UserDeck:
        if not user_id.strip():
            raise ValueError("user_id é obrigatório.")
        if not deck_id.strip():
            raise ValueError("deck_id é obrigatório.")

        deck = await self._deck_repository.find_by_id_and_user_id(deck_id, user_id)
        if not deck:
            raise ValueError("Deck não encontrado.")
        return deck

    async def analyze_deck(self, user_id: str, deck_id: str) -> AnalyzeDeckResponse:
        deck = await self.get_user_deck(user_id, deck_id)
        if not deck.parsed_deck.mainboard or not deck.cards:
            raise ValueError("Deck não está enriquecido. Recadastre o deck para habilitar análise.")

        heuristic_result = build_basic_analysis(deck.parsed_deck, deck.cards)
        llm_result = None
        if self._llm_analysis_service and self._llm_analysis_service.enabled:
            llm_result = await self._llm_analysis_service.analyze(
                parsed_deck=deck.parsed_deck,
                cards=deck.cards,
                format_guess=deck.format_guess,
                goal=deck.goal,
                heuristic_result=heuristic_result,
            )

        result = llm_result or heuristic_result
        return AnalyzeDeckResponse(
            format_guess=deck.format_guess,
            summary=result["summary"],
            strengths=result["strengths"],
            weaknesses=result["weaknesses"],
            suggestions=result["suggestions"],
            parsed_deck=deck.parsed_deck,
            card_count=deck.card_count,
            sideboard_count=deck.sideboard_count,
            analysis_source="llm" if llm_result else "heuristic",
        )
