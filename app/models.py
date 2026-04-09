from typing import List, Optional
from pydantic import BaseModel, Field


class DeckEntry(BaseModel):
    quantity: int = Field(..., ge=1)
    card_name: str


class ParsedDeck(BaseModel):
    mainboard: List[DeckEntry]
    sideboard: List[DeckEntry]


class AnalyzeDeckRequest(BaseModel):
    decklist: str
    format_hint: Optional[str] = None
    goal: Optional[str] = "general improvement"


class CardData(BaseModel):
    name: str
    mana_cost: Optional[str] = None
    cmc: Optional[float] = None
    type_line: Optional[str] = None
    oracle_text: Optional[str] = None
    colors: List[str] = Field(default_factory=list)
    color_identity: List[str] = Field(default_factory=list)
    legalities: dict = Field(default_factory=dict)
    image_url: Optional[str] = None
    scryfall_uri: Optional[str] = None


class AnalyzeDeckResponse(BaseModel):
    format_guess: str
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    parsed_deck: ParsedDeck
    card_count: int
    sideboard_count: int


class HealthResponse(BaseModel):
    status: str
    version: str
