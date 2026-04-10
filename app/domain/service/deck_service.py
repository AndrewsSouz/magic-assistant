from __future__ import annotations
import logging

from app.contract.models.analyze_deck_request import AnalyzeDeckRequest
from app.contract.models.analyze_deck_response import AnalyzeDeckResponse
from app.domain.service.analise_service import build_basic_analysis, guess_format
from app.domain.service.card_service import CardService
from app.domain.service.llm_analysis_service import LlmAnalysisService
from app.domain.util.deck_parser import parse_decklist


class DeckService:
    def __init__(
        self,
        card_service: CardService,
        llm_analysis_service: LlmAnalysisService | None = None,
    ) -> None:
        self._card_service = card_service
        self._llm_analysis_service = llm_analysis_service

    async def analyze(self, request: AnalyzeDeckRequest) -> AnalyzeDeckResponse:
        parsed_deck = parse_decklist(request.decklist)
        if not parsed_deck.mainboard:
            raise ValueError("Decklist inválida ou vazia.")

        cards = await self._card_service.fetch_cards(
            [item.card_name for item in parsed_deck.mainboard]
        )
        format_guess = request.format_hint or guess_format(parsed_deck)
        heuristic_result = build_basic_analysis(parsed_deck, cards)
        llm_result = None
        if self._llm_analysis_service:
            llm_result = await self._llm_analysis_service.analyze(
                parsed_deck=parsed_deck,
                cards=cards,
                format_guess=format_guess,
                goal=request.goal,
                heuristic_result=heuristic_result,
            )
            logging.info(f"LLM analysis result: {llm_result}")
        result = llm_result or heuristic_result

        return AnalyzeDeckResponse(
            format_guess=format_guess,
            summary=result["summary"],
            strengths=result["strengths"],
            weaknesses=result["weaknesses"],
            suggestions=result["suggestions"],
            parsed_deck=parsed_deck,
            card_count=result["card_count"],
            sideboard_count=result["sideboard_count"],
            analysis_source="llm" if llm_result else "heuristic",
        )
