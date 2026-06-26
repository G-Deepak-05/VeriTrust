"""
Dashboard and analytics schemas.
"""

from pydantic import Field

from app.schemas.common import BaseSchema


class DashboardStats(BaseSchema):
    """High-level stats for the org dashboard."""

    total_verifications: int
    approved_count: int
    review_count: int
    rejected_count: int
    approval_rate: float = Field(..., description="Percentage 0-100")
    average_risk_score: float
    api_keys_active: int
    total_members: int


class TimeSeriesPoint(BaseSchema):
    date: str  # ISO date string e.g. "2024-01-15"
    total: int
    approved: int
    review: int
    rejected: int
    avg_risk_score: float


class AnalyticsResponse(BaseSchema):
    """Time-series analytics for verification trends."""

    success: bool = True
    period: str  # "7d", "30d", "90d"
    data: list[TimeSeriesPoint]
    summary: DashboardStats
