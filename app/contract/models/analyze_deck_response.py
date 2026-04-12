from pydantic import BaseModel


class AnalyzeDeckResponse(BaseModel):
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    card_count: int
    sideboard_count: int
    analysis_source: str


class AnalyzeDeckAcceptedResponse(BaseModel):
    deck_id: str
    analysis_status: str
    message: str
