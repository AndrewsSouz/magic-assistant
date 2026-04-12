from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.models.card.card_data import CardData


class UserDeckResponse(BaseModel):
    id: str
    user_id: str
    name: str
    raw_decklist: str
    cards: list[CardData] = Field(default_factory=list)
    format_guess: str | None = None
    card_count: int = 0
    sideboard_count: int = 0
    enrichment_status: str
    enrichment_error: str | None = None
    enrichment_started_at: datetime | None = None
    enrichment_completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    format_hint: str | None = None
    goal: str | None = None
