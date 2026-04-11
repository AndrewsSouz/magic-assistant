from pydantic import BaseModel


class UserDeckResponse(BaseModel):
    id: str
    user_id: str
    name: str
    decklist: str
    format_hint: str | None = None
    goal: str | None = None
