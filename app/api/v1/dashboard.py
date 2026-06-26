"""
Dashboard and analytics router.
"""
from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.dashboard import AnalyticsResponse, DashboardStats
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: CurrentUser,
    db: DBSession,
) -> DashboardStats:
    """Return high-level stats for the current organization."""
    if not current_user.organization_id:
        from app.core.exceptions import ValidationError
        raise ValidationError("User does not belong to an organization")
    return await DashboardService(db).get_stats(current_user.organization_id)


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    current_user: CurrentUser,
    db: DBSession,
    period: str = Query(default="30d", pattern="^(7d|30d|90d)$"),
) -> AnalyticsResponse:
    """Return time-series verification analytics for the organization."""
    if not current_user.organization_id:
        from app.core.exceptions import ValidationError
        raise ValidationError("User does not belong to an organization")
    return await DashboardService(db).get_analytics(current_user.organization_id, period)
