"""Auth-related Pydantic schemas (sign-up, login, token response)."""

from pydantic import BaseModel, EmailStr, field_validator

from src.models.enums import UserRole


class SignUpInput(BaseModel):
    """Payload for creating a new user account."""

    name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        """Enforce a minimum password length of 8 characters."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginInput(BaseModel):
    """Payload for authenticating an existing user."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT bearer token returned after successful auth."""

    access_token: str
    token_type: str = "bearer"
