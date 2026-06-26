"""
Dashboard analytics service.
"""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verification import VerificationRequest, VerificationResult
from app.repositories.api_key_repository import APIKeyRepository
from app.repositories.user_repository import UserRepository
from app.repositories.verification_repository import VerificationRepository
from app.schemas.dashboard import AnalyticsResponse, DashboardStats, TimeSeriesPoint


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.verify_repo = VerificationRepository(db)
        self.api_key_repo = APIKeyRepository(db)
        self.user_repo = UserRepository(db)

    async def get_stats(self, org_id: uuid.UUID) -> DashboardStats:
        stats = await self.verify_repo.get_stats(org_id)

        # Active API keys
        keys = await self.api_key_repo.get_by_org(org_id)
        active_keys = sum(1 for k in keys if k.is_active)

        # Total members
        _, member_count = await self.user_repo.get_by_org(org_id, limit=1)

        return DashboardStats(
            total_verifications=stats["total"],
            approved_count=stats["approved"],
            review_count=stats["review"],
            rejected_count=stats["rejected"],
            approval_rate=stats["approval_rate"],
            average_risk_score=stats["avg_risk_score"],
            api_keys_active=active_keys,
            total_members=member_count,
        )

    async def get_analytics(
        self, org_id: uuid.UUID, period: str = "30d"
    ) -> AnalyticsResponse:
        """Return time-series verification data grouped by day."""
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        since = datetime.now(UTC) - timedelta(days=days)

        # Query daily counts
        rows = await self.db.execute(
            select(
                func.date(VerificationRequest.created_at).label("date"),
                VerificationResult.decision,
                func.count(VerificationResult.id).label("count"),
                func.avg(VerificationResult.risk_score).label("avg_score"),
            )
            .join(VerificationResult, VerificationResult.request_id == VerificationRequest.id)
            .where(
                VerificationRequest.organization_id == org_id,
                VerificationRequest.created_at >= since,
            )
            .group_by(func.date(VerificationRequest.created_at), VerificationResult.decision)
            .order_by(func.date(VerificationRequest.created_at))
        )

        # Aggregate by date
        date_map: dict[str, dict] = {}
        for row in rows:
            date_str = str(row.date)
            if date_str not in date_map:
                date_map[date_str] = {
                    "total": 0,
                    "approved": 0,
                    "review": 0,
                    "rejected": 0,
                    "scores": [],
                }
            date_map[date_str]["total"] += row.count
            date_map[date_str]["scores"].append(float(row.avg_score or 0))
            if row.decision == "APPROVED":
                date_map[date_str]["approved"] += row.count
            elif row.decision == "REVIEW":
                date_map[date_str]["review"] += row.count
            elif row.decision == "REJECT":
                date_map[date_str]["rejected"] += row.count

        data = [
            TimeSeriesPoint(
                date=d,
                total=v["total"],
                approved=v["approved"],
                review=v["review"],
                rejected=v["rejected"],
                avg_risk_score=round(sum(v["scores"]) / len(v["scores"]), 2) if v["scores"] else 0.0,
            )
            for d, v in sorted(date_map.items())
        ]

        stats = await self.get_stats(org_id)
        return AnalyticsResponse(period=period, data=data, summary=stats)
