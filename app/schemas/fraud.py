"""
Fraud rule schemas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class FraudRuleCreate(BaseSchema):
    rule_name: str = Field(..., min_length=2, max_length=100, examples=["vpn_detected"])
    rule_type: str = Field(..., examples=["ip", "email", "device", "phone", "velocity", "geo"])
    description: str = Field(..., max_length=500)
    score_impact: int = Field(..., ge=0, le=100, examples=[20])
    is_active: bool = Field(default=True)
    config: dict = Field(default_factory=dict)


class FraudRuleUpdate(BaseSchema):
    description: str | None = None
    score_impact: int | None = Field(None, ge=0, le=100)
    is_active: bool | None = None
    config: dict | None = None


class FraudRuleResponse(BaseSchema):
    id: UUID
    organization_id: UUID | None = None
    rule_name: str
    rule_type: str
    description: str
    score_impact: int
    is_active: bool
    config: dict
    created_at: datetime
    updated_at: datetime


class SimulateRequest(BaseSchema):
    """Dry-run a verification without persisting the result."""

    name: str
    email: str
    phone: str | None = None
    pan: str | None = None
    ip_address: str | None = None
    device_id: str | None = None


class SimulateResponse(BaseSchema):
    """Result of fraud simulation — no DB writes."""

    success: bool = True
    risk_score: int
    decision: str
    reasons: list[str]
    rule_breakdown: dict
