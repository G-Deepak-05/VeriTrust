"""
Fraud Rule Engine — evaluates configurable rules and produces risk scores.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.fraud_rule import FraudRule
from app.repositories.fraud_rule_repository import FraudRuleRepository
from app.schemas.fraud import (
    FraudRuleCreate,
    FraudRuleResponse,
    FraudRuleUpdate,
    SimulateRequest,
    SimulateResponse,
)
from app.utils.validators import (
    is_disposable_email,
    is_valid_pan,
)

logger = get_logger(__name__)


@dataclass
class RuleEvaluationResult:
    total_score: int = 0
    reasons: list[str] = field(default_factory=list)
    breakdown: dict[str, int] = field(default_factory=dict)


def _make_decision(score: int) -> str:
    """Map risk score to a decision label per PRD spec."""
    if score <= 30:
        return "APPROVED"
    elif score <= 60:
        return "REVIEW"
    return "REJECT"


class FraudService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = FraudRuleRepository(db)

    def evaluate_rules(
        self,
        rules: list[FraudRule],
        *,
        email: str,
        phone: str | None,
        pan: str | None,
        ip_address: str | None,
        device_id: str | None,
        device_seen_before: bool = False,
        phone_seen_before: bool = False,
        device_blacklisted: bool = False,
        ip_request_count: int = 0,
    ) -> RuleEvaluationResult:
        """
        Evaluate all applicable fraud rules against the verification payload.

        Returns aggregated score (clamped 0-100), reasons, and per-rule breakdown.
        """
        result = RuleEvaluationResult()

        for rule in rules:
            if not rule.is_active:
                continue

            triggered = False
            match rule.rule_type:
                case "email":
                    if rule.rule_name == "disposable_email" and email:
                        triggered = is_disposable_email(email)

                case "document":
                    if rule.rule_name == "invalid_pan_format" and pan:
                        triggered = not is_valid_pan(pan)

                case "phone":
                    if rule.rule_name == "phone_reused" and phone:
                        triggered = phone_seen_before

                case "device":
                    if rule.rule_name == "blacklisted_device" and device_id:
                        triggered = device_blacklisted

                case "velocity":
                    if rule.rule_name == "high_velocity" and ip_address:
                        threshold = rule.config.get("max_requests", 5)
                        triggered = ip_request_count >= threshold

                case "geo":
                    # Country mismatch — simplified: check if IP is private/reserved
                    if rule.rule_name == "country_mismatch" and ip_address and phone:
                        # In a real system: geolocate IP and compare to phone country
                        # For MVP: flag if IP is non-Indian private range with +91 phone
                        triggered = False  # Stub — extendable

                case _:
                    logger.debug("Unknown rule type", rule_type=rule.rule_type)

            if triggered:
                result.total_score += rule.score_impact
                result.reasons.append(rule.description or rule.rule_name)
                result.breakdown[rule.rule_name] = rule.score_impact

        # Clamp to 0-100
        result.total_score = min(100, max(0, result.total_score))
        return result

    async def simulate(self, org_id: uuid.UUID | None, data: SimulateRequest) -> SimulateResponse:
        """Dry-run fraud evaluation — no DB writes."""
        rules = await self.repo.get_active_rules(org_id)
        result = self.evaluate_rules(
            rules,
            email=data.email,
            phone=data.phone,
            pan=data.pan,
            ip_address=data.ip_address,
            device_id=data.device_id,
        )
        return SimulateResponse(
            risk_score=result.total_score,
            decision=_make_decision(result.total_score),
            reasons=result.reasons,
            rule_breakdown=result.breakdown,
        )

    async def list_rules(self, org_id: uuid.UUID | None) -> list[FraudRuleResponse]:
        rules = await self.repo.get_by_org(org_id)
        return [FraudRuleResponse.model_validate(r) for r in rules]

    async def create_rule(self, org_id: uuid.UUID, data: FraudRuleCreate) -> FraudRuleResponse:
        rule = await self.repo.create(
            organization_id=org_id,
            rule_name=data.rule_name,
            rule_type=data.rule_type,
            description=data.description,
            score_impact=data.score_impact,
            is_active=data.is_active,
            config=data.config,
        )
        return FraudRuleResponse.model_validate(rule)

    async def update_rule(
        self, rule_id: uuid.UUID, org_id: uuid.UUID, data: FraudRuleUpdate
    ) -> FraudRuleResponse:
        rule = await self.repo.get(rule_id)
        if not rule or (rule.organization_id and rule.organization_id != org_id):
            raise NotFoundError("Fraud Rule", str(rule_id))
        updates = data.model_dump(exclude_none=True)
        rule = await self.repo.update(rule, **updates)
        return FraudRuleResponse.model_validate(rule)

    async def delete_rule(self, rule_id: uuid.UUID, org_id: uuid.UUID) -> None:
        rule = await self.repo.get(rule_id)
        if not rule or rule.organization_id != org_id:
            raise NotFoundError("Fraud Rule", str(rule_id))
        await self.repo.delete(rule)


def make_decision(score: int) -> str:
    """Public export of decision mapping."""
    return _make_decision(score)
