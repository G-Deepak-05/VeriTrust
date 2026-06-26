"""Verification repository."""
from uuid import UUID

from sqlalchemy import func, select

from app.models.verification import VerificationRequest, VerificationResult
from app.repositories.base_repository import BaseRepository


class VerificationRepository(BaseRepository[VerificationRequest]):
    model = VerificationRequest

    async def get_by_org(
        self, org_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[VerificationRequest], int]:
        return await self.get_multi(
            filters=[VerificationRequest.organization_id == org_id],
            offset=offset,
            limit=limit,
        )

    async def get_stats(self, org_id: UUID) -> dict:
        """Aggregate counts and average score for an organization."""
        # Count by decision
        rows = await self.db.execute(
            select(VerificationResult.decision, func.count(VerificationResult.id))
            .join(VerificationRequest, VerificationResult.request_id == VerificationRequest.id)
            .where(VerificationRequest.organization_id == org_id)
            .group_by(VerificationResult.decision)
        )
        decision_counts = {row[0]: row[1] for row in rows}

        # Average risk score
        avg_score = await self.db.scalar(
            select(func.avg(VerificationResult.risk_score))
            .join(VerificationRequest, VerificationResult.request_id == VerificationRequest.id)
            .where(VerificationRequest.organization_id == org_id)
        )

        total = sum(decision_counts.values())
        approved = decision_counts.get("APPROVED", 0)

        return {
            "total": total,
            "approved": approved,
            "review": decision_counts.get("REVIEW", 0),
            "rejected": decision_counts.get("REJECT", 0),
            "approval_rate": round((approved / total * 100), 2) if total > 0 else 0.0,
            "avg_risk_score": round(float(avg_score or 0), 2),
        }
