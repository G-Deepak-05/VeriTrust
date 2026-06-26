"""
API Key schemas.
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class APIKeyCreate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255, examples=["Production Key"])
    permissions: dict = Field(
        default_factory=dict,
        description="Key-level permission overrides",
        examples=[{"verify": True, "read_audit": False}],
    )


class APIKeyResponse(BaseSchema):
    """Response after listing keys — secret is NEVER shown here."""
    id: UUID
    name: str
    key_prefix: str
    is_active: bool
    last_used_at: datetime | None = None
    permissions: dict
    created_at: datetime


class APIKeyCreatedResponse(BaseSchema):
    """
    Response immediately after key creation — secret shown ONCE only.
    Clients must store this securely; it cannot be retrieved again.
    """
    success: bool = True
    message: str = "Store this key securely — it will not be shown again."
    id: UUID
    name: str
    key: str  # Full key shown once
    key_prefix: str
    created_at: datetime
