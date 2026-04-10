from pydantic import BaseModel

from app.domain.models.deck.deck_entry import DeckEntry


class ParsedDeck(BaseModel):
    mainboard: list[DeckEntry]
    sideboard: list[DeckEntry]
