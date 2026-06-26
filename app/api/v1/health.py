"""
Health check router — liveness and readiness probes.
"""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.dependencies import DBSession, RedisClient
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check(db: DBSession, redis: RedisClient) -> HealthResponse:
    """
    Liveness + readiness probe.

    Checks PostgreSQL and Redis connectivity.
    Used by Docker healthchecks and monitoring.
    """
    # PostgreSQL check
    postgres_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        postgres_status = f"error: {e}"

    # Redis check
    redis_status = "ok"
    try:
        await redis.ping()
    except Exception as e:
        redis_status = f"error: {e}"

    return HealthResponse(
        status="healthy" if postgres_status == "ok" and redis_status == "ok" else "degraded",
        version=settings.app_version,
        postgres=postgres_status,
        redis=redis_status,
        environment=settings.environment,
    )
