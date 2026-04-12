from pydantic import BaseModel, Field


class DeckAnalysis(BaseModel):
    format_guess: str
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    card_count: int
    sideboard_count: int
    analysis_source: str
