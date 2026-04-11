from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from app.contract.models.analyze_deck_response import AnalyzeDeckResponse
from app.domain.models.card.card_data import CardData
from app.domain.models.deck.deck_entry import DeckEntry
from app.domain.models.deck.user_deck import UserDeck
from app.domain.service.analise_service import build_basic_analysis, guess_format
from app.domain.service.card_service import CardService
from app.domain.service.llm_analysis_service import LlmAnalysisService
from app.domain.util.deck_parser import parse_decklist
from app.integration.card_integration import CardEnrichmentError
from app.integration.deck_repository import DeckRepository
from app.integration.user_repository import UserRepository

log = logging.getLogger(__name__)


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
        self._background_tasks: set[asyncio.Task] = set()

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
        self._validate_create_deck_inputs(user_id, name, decklist)

        user = await self._user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("Usuário não encontrado.")

        parsed_deck = parse_decklist(decklist)
        if not parsed_deck.mainboard:
            raise ValueError("Decklist inválida ou vazia.")

        now = self._utcnow()
        deck = UserDeck(
            id="",
            user_id=user_id,
            name=name.strip(),
            raw_decklist=decklist.strip(),
            parsed_deck=parsed_deck,
            cards=[],
            format_guess=None,
            card_count=0,
            sideboard_count=0,
            enrichment_status="pending",
            enrichment_error=None,
            enrichment_started_at=None,
            enrichment_completed_at=None,
            created_at=now,
            updated_at=now,
            format_hint=format_hint,
            goal=goal,
        )

        log.info("Creating deck for user %s", user_id)
        return await self._deck_repository.create(deck)

    async def enrich_deck(self, user_id: str, deck_id: str) -> None:
        deck = await self.get_user_deck(user_id, deck_id)
        unique_names = self._extract_unique_card_names(deck)
        started_at = time.perf_counter()

        log.info("Enrichment started for deck %s", deck_id)
        log.info("Deck %s has %s unique card(s)", deck_id, len(unique_names))
        log.info(
            "Deck %s will be sent in %s batch(es) to Scryfall collection",
            deck_id,
            (len(unique_names) + 74) // 75 if unique_names else 0,
        )

        await self._deck_repository.mark_enrichment_processing(deck_id)

        try:
            unique_cards = await self._card_service.fetch_cards_by_exact_names(unique_names)
            card_map = {card.name.casefold(): card for card in unique_cards}
            missing_names = [
                name for name in unique_names
                if name.casefold() not in card_map
            ]
            if missing_names:
                raise CardEnrichmentError(f"Cards not found: {missing_names}")

            ordered_cards = self._build_ordered_cards(deck, card_map)
            format_guess = deck.format_hint or guess_format(deck.parsed_deck)

            await self._deck_repository.complete_enrichment(
                deck_id,
                cards=[card.model_dump(mode="json") for card in ordered_cards],
                format_guess=format_guess,
                card_count=sum(item.quantity for item in deck.parsed_deck.mainboard),
                sideboard_count=sum(item.quantity for item in deck.parsed_deck.sideboard),
            )
            elapsed = round(time.perf_counter() - started_at, 2)
            log.info("Enrichment completed for deck %s in %s seconds", deck_id, elapsed)
        except Exception as exc:
            await self._deck_repository.fail_enrichment(deck_id, str(exc))
            log.exception("Enrichment failed for deck %s: %s", deck_id, exc)

    async def retry_enrichment(self, user_id: str, deck_id: str) -> UserDeck:
        deck = await self.get_user_deck(user_id, deck_id)
        if deck.enrichment_status != "failed":
            raise ValueError("Retry só é permitido para decks com status failed.")

        await self._deck_repository.reset_enrichment(deck_id)
        return await self.get_user_deck(user_id, deck_id)

    def schedule_enrichment(self, user_id: str, deck_id: str) -> None:
        task = asyncio.create_task(self.enrich_deck(user_id, deck_id))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

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

        if deck.enrichment_status in {"pending", "processing"}:
            raise ValueError("Deck ainda está sendo enriquecido")
        if deck.enrichment_status == "failed":
            raise ValueError("Falha no enriquecimento do deck. Tente reprocessar")
        if deck.enrichment_status != "completed":
            raise ValueError("Deck não está pronto para análise")

        mainboard_cards = deck.cards[:len(deck.parsed_deck.mainboard)]
        heuristic_result = build_basic_analysis(deck.parsed_deck, mainboard_cards)
        llm_result = None
        if self._llm_analysis_service and self._llm_analysis_service.enabled:
            llm_result = await self._llm_analysis_service.analyze(
                parsed_deck=deck.parsed_deck,
                cards=mainboard_cards,
                format_guess=deck.format_guess or "Desconhecido",
                goal=deck.goal,
                heuristic_result=heuristic_result,
            )

        result = llm_result or heuristic_result
        return AnalyzeDeckResponse(
            format_guess=deck.format_guess or "Desconhecido",
            summary=result["summary"],
            strengths=result["strengths"],
            weaknesses=result["weaknesses"],
            suggestions=result["suggestions"],
            parsed_deck=deck.parsed_deck,
            card_count=deck.card_count,
            sideboard_count=deck.sideboard_count,
            analysis_source="llm" if llm_result else "heuristic",
        )

    @staticmethod
    def _validate_create_deck_inputs(user_id: str, name: str, decklist: str) -> None:
        if not user_id.strip():
            raise ValueError("user_id é obrigatório.")
        if not name.strip():
            raise ValueError("name é obrigatório.")
        if not decklist.strip():
            raise ValueError("decklist é obrigatório.")

    @staticmethod
    def _extract_unique_card_names(deck: UserDeck) -> list[str]:
        names = [
            entry.card_name
            for entry in [*deck.parsed_deck.mainboard, *deck.parsed_deck.sideboard]
        ]
        seen: set[str] = set()
        unique_names: list[str] = []
        for name in names:
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique_names.append(name)
        return unique_names

    @staticmethod
    def _build_ordered_cards(deck: UserDeck, card_map: dict[str, CardData]) -> list[CardData]:
        ordered_entries: list[DeckEntry] = [
            *deck.parsed_deck.mainboard,
            *deck.parsed_deck.sideboard,
        ]
        return [card_map[entry.card_name.casefold()] for entry in ordered_entries]

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)
