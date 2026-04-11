from pydantic import BaseModel, EmailStr, Field


class RegisterUserRequest(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=6, max_length=200)
