from pydantic import BaseModel


class ResetPasswordResponse(BaseModel):
    message: str
