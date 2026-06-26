"""Fraud rule repository."""

from uuid import UUID

from sqlalchemy import or_, select

from app.models.fraud_rule import FraudRule
from app.repositories.base_repository import BaseRepository


class FraudRuleRepository(BaseRepository[FraudRule]):
    model = FraudRule

    async def get_active_rules(self, org_id: UUID | None = None) -> list[FraudRule]:
        """
        Get all active rules applicable to an org.
        Returns global rules (org_id IS NULL) + org-specific rules.
        """
        query = (
            select(FraudRule)
            .where(
                FraudRule.is_active == True,  # noqa: E712
                or_(FraudRule.organization_id.is_(None), FraudRule.organization_id == org_id),
            )
            .order_by(FraudRule.score_impact.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_org(self, org_id: UUID | None) -> list[FraudRule]:
        """Get all rules for a specific org (including globals)."""
        query = (
            select(FraudRule)
            .where(or_(FraudRule.organization_id.is_(None), FraudRule.organization_id == org_id))
            .order_by(FraudRule.created_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
