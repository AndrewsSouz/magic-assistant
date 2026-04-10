from typing import Optional

from pydantic import BaseModel, Field


class CardData(BaseModel):
    name: str
    mana_cost: Optional[str] = None
    cmc: Optional[float] = None
    type_line: Optional[str] = None
    oracle_text: Optional[str] = None
    colors: list[str] = Field(default_factory=list)
    color_identity: list[str] = Field(default_factory=list)
    legalities: dict = Field(default_factory=dict)
    image_url: Optional[str] = None
    scryfall_uri: Optional[str] = None
