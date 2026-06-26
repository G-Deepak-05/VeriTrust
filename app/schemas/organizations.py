"""
Organization schemas.
"""

from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class OrgCreate(BaseSchema):
    name: str = Field(..., min_length=2, max_length=255, examples=["Acme Corp"])
    description: str | None = Field(None, max_length=1000)
    website: str | None = Field(None, examples=["https://acme.com"])


class OrgUpdate(BaseSchema):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    website: str | None = None


class OrgResponse(BaseSchema):
    id: UUID
    name: str
    slug: str
    description: str | None = None
    website: str | None = None
    is_active: bool
    owner_id: UUID


class InviteMemberRequest(BaseSchema):
    email: str = Field(..., description="Email of the user to invite")
    role: str = Field(..., pattern="^(admin|analyst|developer)$", examples=["developer"])
