"""
Verification request/result schemas.
"""
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema


class VerificationInput(BaseSchema):
    """Input payload for a verification request — matches PRD spec."""
    name: str = Field(..., min_length=2, max_length=255, examples=["John Doe"])
    email: str = Field(..., examples=["john@gmail.com"])
    phone: str | None = Field(None, examples=["+919999999999"])
    pan: str | None = Field(None, examples=["ABCDE1234F"])
    ip_address: str | None = Field(None, examples=["103.44.12.34"])
    device_id: str | None = Field(None, examples=["device_123"])

    @field_validator("pan", mode="before")
    @classmethod
    def uppercase_pan(cls, v: str | None) -> str | None:
        return v.upper().strip() if v else v


class VerificationResponse(BaseSchema):
    """Output from the verification pipeline — matches PRD spec."""
    success: bool = True
    verification_id: UUID
    risk_score: int = Field(..., ge=0, le=100)
    decision: str = Field(..., examples=["APPROVED", "REVIEW", "REJECT"])
    reasons: list[str] = Field(default_factory=list)
    processing_ms: int
    created_at: datetime


class VerificationDetailResponse(VerificationResponse):
    """Extended response with full input and rule breakdown."""
    name: str
    email: str
    phone: str | None = None
    pan: str | None = None
    ip_address: str | None = None
    device_id: str | None = None
    status: str
    rule_breakdown: dict


class VerificationHistoryItem(BaseSchema):
    """Summary row for history list."""
    verification_id: UUID
    email: str
    risk_score: int
    decision: str
    status: str
    created_at: datetime
