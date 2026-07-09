from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole


class SignupRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(pattern=r"^01[0-9]-?\d{3,4}-?\d{4}$")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    name: str
    phone: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
