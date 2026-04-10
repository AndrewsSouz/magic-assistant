from typing import Optional

from pydantic import BaseModel


class AnalyzeDeckRequest(BaseModel):
    decklist: str
    format_hint: Optional[str] = None
    goal: Optional[str] = "general improvement"
