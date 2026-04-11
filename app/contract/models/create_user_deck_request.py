from pydantic import BaseModel, Field


class CreateUserDeckRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    decklist: str = Field(..., min_length=1)
    format_hint: str | None = None
    goal: str | None = None
