"""
Authentication schemas.
"""
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import BaseSchema


class RegisterRequest(BaseSchema):
    full_name: str = Field(..., min_length=2, max_length=255, examples=["John Doe"])
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["SecurePass123!"])
    organization_name: str = Field(..., min_length=2, max_length=255, examples=["Acme Corp"])

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseSchema):
    email: EmailStr = Field(..., examples=["john@example.com"])
    password: str = Field(..., examples=["SecurePass123!"])


class TokenResponse(BaseSchema):
    success: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseSchema):
    refresh_token: str = Field(..., description="The refresh token received during login")


class ForgotPasswordRequest(BaseSchema):
    email: EmailStr


class UserResponse(BaseSchema):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    organization_id: UUID | None = None
