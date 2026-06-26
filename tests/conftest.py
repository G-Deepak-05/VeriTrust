"""
Pytest configuration and shared fixtures for VeriTrust tests.
"""
import asyncio
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

# ─── Test Database ────────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite+aiosqlite:///./test_veritrust.db"


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a fresh test database engine per test function."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async DB session for tests."""
    session_factory = async_sessionmaker(
        bind=db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.sismember = AsyncMock(return_value=False)
    redis.ping = AsyncMock(return_value=True)
    redis.pipeline = MagicMock(return_value=AsyncMock(execute=AsyncMock(return_value=[])))
    return redis


# ─── App Fixture ──────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="function")
async def app(db_session, mock_redis) -> FastAPI:
    """Create test FastAPI app with dependency overrides."""
    from app.core.dependencies import get_redis

    test_app = create_app()

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return mock_redis

    test_app.dependency_overrides[get_db] = override_get_db
    test_app.dependency_overrides[get_redis] = override_get_redis
    return test_app


@pytest_asyncio.fixture(scope="function")
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for endpoint testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ─── Factory Fixtures ─────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def test_org(db_session) -> Any:
    """Create a test organization."""
    from app.models.organization import Organization

    org = Organization(
        id=uuid.uuid4(),
        name="Test Corp",
        slug="test-corp",
        owner_id=uuid.uuid4(),
        is_active=True,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session, test_org) -> Any:
    """Create a test admin user."""
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        email="admin@testcorp.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Test Admin",
        role="admin",
        organization_id=test_org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user) -> dict[str, str]:
    """Generate valid JWT auth headers for a test user."""
    token = create_access_token(
        subject=str(test_user.id),
        extra_claims={"role": test_user.role, "org_id": str(test_user.organization_id)},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_api_key(db_session, test_org) -> tuple[Any, str]:
    """Create a test API key and return (model, full_key)."""
    from app.core.security import create_api_key_secret
    from app.models.api_key import APIKey

    full_key, hashed = create_api_key_secret()
    key = APIKey(
        id=uuid.uuid4(),
        organization_id=test_org.id,
        name="Test Key",
        key_prefix=full_key[:12],
        hashed_secret=hashed,
        is_active=True,
        permissions={},
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)
    return key, full_key


@pytest_asyncio.fixture
async def test_fraud_rules(db_session, test_org) -> list[Any]:
    """Seed default fraud rules for tests."""
    from app.models.fraud_rule import FraudRule

    rules = [
        FraudRule(rule_name="disposable_email", rule_type="email", description="Disposable email", score_impact=25, is_active=True, config={}),
        FraudRule(rule_name="invalid_pan_format", rule_type="document", description="Invalid PAN", score_impact=20, is_active=True, config={}),
        FraudRule(rule_name="phone_reused", rule_type="phone", description="Phone reused", score_impact=15, is_active=True, config={"max_count": 3}),
        FraudRule(rule_name="blacklisted_device", rule_type="device", description="Blacklisted device", score_impact=30, is_active=True, config={}),
        FraudRule(rule_name="high_velocity", rule_type="velocity", description="High velocity", score_impact=25, is_active=True, config={"max_requests": 5, "window_seconds": 3600}),
    ]
    for rule in rules:
        db_session.add(rule)
    await db_session.commit()
    return rules
