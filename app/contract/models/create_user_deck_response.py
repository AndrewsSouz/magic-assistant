from pydantic import BaseModel


class CreateUserDeckResponse(BaseModel):
    id: str
    name: str
    enrichment_status: str
    message: str
