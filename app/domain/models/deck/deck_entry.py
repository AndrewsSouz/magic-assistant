from pydantic import BaseModel, Field


class DeckEntry(BaseModel):
    quantity: int = Field(..., ge=1)
    card_name: str
    zone: str = "mainboard"
    raw_line: str | None = None
    set_code: str | None = None
    collector_number: str | None = None
