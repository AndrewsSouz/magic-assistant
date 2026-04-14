from pydantic import BaseModel, EmailStr


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr
