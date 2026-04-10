from pydantic import BaseModel, Field


class DeckEntry(BaseModel):
    quantity: int = Field(..., ge=1)
    card_name: str
