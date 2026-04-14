from pydantic import BaseModel, Field

from app.domain.models.deck.deck_entry import DeckEntry


class ParsedDeck(BaseModel):
    mainboard: list[DeckEntry]
    sideboard: list[DeckEntry]
    unparsed_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    detected_sections: list[str] = Field(default_factory=list)
