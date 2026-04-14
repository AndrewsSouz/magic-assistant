from pydantic import BaseModel, Field


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1, max_length=500)
    new_password: str = Field(..., min_length=6, max_length=200)
