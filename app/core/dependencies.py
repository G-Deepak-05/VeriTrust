"""
FastAPI dependency injection factories.
Provides reusable dependencies for DB sessions, Redis, authentication, and RBAC.
"""
from typing import Annotated
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    APIKeyInvalidError,
    AuthenticationError,
    InsufficientPermissionsError,
    InvalidTokenError,
)
from app.core.security import decode_access_token, hash_api_key
from app.db.session import get_db  # noqa: F401 — re-exported
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── HTTP Bearer scheme ───────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)

# ─── Redis ────────────────────────────────────────────────────────────────────
_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return a shared async Redis client."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


# ─── Current User ─────────────────────────────────────────────────────────────
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> "UserModel":  # type: ignore[name-defined]  # noqa: F821
    """
    Extract and validate JWT Bearer token, return current user.
    Raises 401 if token is missing, invalid, or user not found.
    """
    # Import here to avoid circular imports
    from app.models.user import User
    from app.repositories.user_repository import UserRepository

    if not credentials:
        raise AuthenticationError("Authorization header missing")

    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise InvalidTokenError()

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Token missing subject claim")

    repo = UserRepository(db)
    user = await repo.get(UUID(user_id))
    if not user:
        raise AuthenticationError("User not found")

    return user


async def get_current_active_user(
    current_user: Annotated["UserModel", Depends(get_current_user)],  # type: ignore[name-defined]  # noqa: F821
) -> "UserModel":  # type: ignore[name-defined]  # noqa: F821
    """Ensure the current user account is active."""
    if not current_user.is_active:
        raise AuthenticationError("Account is deactivated")
    return current_user


# ─── RBAC ─────────────────────────────────────────────────────────────────────
def require_roles(*roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_roles("admin"))])
    """

    async def check_roles(
        current_user: Annotated["UserModel", Depends(get_current_active_user)],  # type: ignore[name-defined]  # noqa: F821
    ) -> "UserModel":  # type: ignore[name-defined]  # noqa: F821
        if current_user.role not in roles:
            raise InsufficientPermissionsError(
                f"Role '{current_user.role}' is not authorized. Required: {list(roles)}"
            )
        return current_user

    return check_roles


# ─── API Key Auth ─────────────────────────────────────────────────────────────
async def get_api_key_org(
    x_api_key: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> "OrganizationModel":  # type: ignore[name-defined]  # noqa: F821
    """
    Validate X-Api-Key header and return the associated organization.
    Updates last_used_at timestamp on the key.
    """
    from app.models.organization import Organization
    from app.repositories.api_key_repository import APIKeyRepository

    if not x_api_key:
        raise APIKeyInvalidError()

    hashed = hash_api_key(x_api_key)
    repo = APIKeyRepository(db)
    api_key = await repo.get_by_hash(hashed)

    if not api_key or not api_key.is_active:
        raise APIKeyInvalidError()

    # Non-blocking last_used_at update
    await repo.update_last_used(api_key.id)

    org = api_key.organization
    if not org or not org.is_active:
        from app.core.exceptions import OrganizationInactiveError
        raise OrganizationInactiveError()

    return org


# ─── Type aliases ─────────────────────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]
CurrentUser = Annotated["UserModel", Depends(get_current_active_user)]  # type: ignore[name-defined]  # noqa: F821
