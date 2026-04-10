from __future__ import annotations

from app.domain.service.analise_service import build_basic_analysis, guess_format
from app.contract.models.analyze_deck_request import AnalyzeDeckRequest
from app.contract.models.analyze_deck_response import AnalyzeDeckResponse
from app.domain.service.card_service import CardService
from app.domain.util.deck_parser import parse_decklist


class DeckService:
    def __init__(self, card_service: CardService) -> None:
        self._card_service = card_service

    async def analyze(self, request: AnalyzeDeckRequest) -> AnalyzeDeckResponse:
        parsed_deck = parse_decklist(request.decklist)
        if not parsed_deck.mainboard:
            raise ValueError("Decklist inválida ou vazia.")

        cards = await self._card_service.fetch_cards(
            [item.card_name for item in parsed_deck.mainboard]
        )
        format_guess = request.format_hint or guess_format(parsed_deck)
        result = build_basic_analysis(parsed_deck, cards)

        return AnalyzeDeckResponse(
            format_guess=format_guess,
            summary=result["summary"],
            strengths=result["strengths"],
            weaknesses=result["weaknesses"],
            suggestions=result["suggestions"],
            parsed_deck=parsed_deck,
            card_count=result["card_count"],
            sideboard_count=result["sideboard_count"],
        )
