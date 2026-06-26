"""
VeriTrust — FastAPI application factory.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("VeriTrust starting up", version=settings.app_version, env=settings.environment)

    # Validate DB + Redis on startup
    try:
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.info("PostgreSQL connection verified")
    except Exception as e:
        logger.error("PostgreSQL connection failed", error=str(e))

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        logger.info("Redis connection verified")
    except Exception as e:
        logger.error("Redis connection failed", error=str(e))

    yield

    logger.info("VeriTrust shutting down")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="VeriTrust API",
        description=(
            "Open Source Identity Verification & Fraud Intelligence Platform.\n\n"
            "## Authentication\n"
            "- Use `POST /api/v1/auth/login` to get a JWT access token.\n"
            "- Add `Authorization: Bearer <token>` to protected endpoints.\n"
            "- For verification endpoints, use `X-Api-Key: vt_live_...` instead.\n\n"
            "## Rate Limiting\n"
            "100 requests/minute per API key, 20/minute for unauthenticated requests.\n"
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "VeriTrust", "url": "https://github.com/veritrust"},
        license_info={"name": "MIT"},
    )

    # ─── CORS ────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    app.add_middleware(RateLimitMiddleware)

    # ─── Audit Logging ────────────────────────────────────────────────────────
    app.add_middleware(AuditMiddleware)

    # ─── Exception Handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ─── Prometheus Metrics ───────────────────────────────────────────────────
    if settings.prometheus_enabled:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator
            Instrumentator().instrument(app).expose(app, endpoint="/metrics")
        except ImportError:
            logger.warning("prometheus_fastapi_instrumentator not installed, skipping metrics")

    # ─── Routers ──────────────────────────────────────────────────────────────
    app.include_router(api_v1_router, prefix=settings.api_prefix)

    # ─── UI Static Files ──────────────────────────────────────────────────────
    from fastapi.staticfiles import StaticFiles
    import os
    if os.path.exists("ui"):
        app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

    return app


app = create_app()
