"""
SQLAlchemy async engine and declarative base.
"""
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ─── Async Engine ─────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)


# ─── Declarative Base ─────────────────────────────────────────────────────────
class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


# ─── SQLite-compatible JSONB Fallback ─────────────────────────────────────────
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JSONB_TYPE = JSONB().with_variant(JSON, "sqlite")
