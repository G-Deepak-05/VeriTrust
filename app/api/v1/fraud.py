"""
Fraud rules router.
"""

import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.common import MessageResponse
from app.schemas.fraud import (
    FraudRuleCreate,
    FraudRuleResponse,
    FraudRuleUpdate,
    SimulateRequest,
    SimulateResponse,
)
from app.services.fraud_service import FraudService

router = APIRouter(prefix="/fraud", tags=["Fraud Engine"])


@router.get("/rules", response_model=list[FraudRuleResponse])
async def list_fraud_rules(
    current_user: CurrentUser,
    db: DBSession,
) -> list[FraudRuleResponse]:
    """List all fraud rules (global + org-specific) visible to this organization."""
    return await FraudService(db).list_rules(current_user.organization_id)


@router.post("/rules", response_model=FraudRuleResponse, status_code=201)
async def create_fraud_rule(
    data: FraudRuleCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> FraudRuleResponse:
    """Create a new org-scoped fraud rule."""
    if not current_user.organization_id:
        from app.core.exceptions import ValidationError

        raise ValidationError("User does not belong to an organization")
    return await FraudService(db).create_rule(current_user.organization_id, data)


@router.put("/rules/{rule_id}", response_model=FraudRuleResponse)
async def update_fraud_rule(
    rule_id: uuid.UUID,
    data: FraudRuleUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> FraudRuleResponse:
    """Update an existing fraud rule (org-scoped only)."""
    if not current_user.organization_id:
        from app.core.exceptions import ValidationError

        raise ValidationError("User does not belong to an organization")
    return await FraudService(db).update_rule(rule_id, current_user.organization_id, data)


@router.delete("/rules/{rule_id}", response_model=MessageResponse)
async def delete_fraud_rule(
    rule_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Delete an org-scoped fraud rule."""
    if not current_user.organization_id:
        from app.core.exceptions import ValidationError

        raise ValidationError("User does not belong to an organization")
    await FraudService(db).delete_rule(rule_id, current_user.organization_id)
    return MessageResponse(message="Fraud rule deleted")


@router.post("/simulate", response_model=SimulateResponse)
async def simulate_fraud(
    data: SimulateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> SimulateResponse:
    """
    Dry-run fraud evaluation against current rules.
    No verification record is created.
    """
    return await FraudService(db).simulate(current_user.organization_id, data)
