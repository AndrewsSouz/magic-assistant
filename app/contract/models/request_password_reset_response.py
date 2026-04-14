from pydantic import BaseModel


class RequestPasswordResetResponse(BaseModel):
    message: str
    reset_token: str
    expires_in_minutes: int
