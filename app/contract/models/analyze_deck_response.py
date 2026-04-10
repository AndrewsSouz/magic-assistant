from pydantic import BaseModel

from app.domain.models.deck.parsed_deck import ParsedDeck


class AnalyzeDeckResponse(BaseModel):
    format_guess: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    parsed_deck: ParsedDeck
    card_count: int
    sideboard_count: int
    analysis_source: str
