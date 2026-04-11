from pydantic import BaseModel

from app.domain.models.card.card_data import CardData
from app.domain.models.deck.parsed_deck import ParsedDeck


class UserDeckResponse(BaseModel):
    id: str
    user_id: str
    name: str
    decklist: str
    parsed_deck: ParsedDeck
    cards: list[CardData]
    format_guess: str
    card_count: int
    sideboard_count: int
    format_hint: str | None = None
    goal: str | None = None
