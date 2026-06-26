"""
Authentication service — register, login, token rotation, logout.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.organization_service import OrganizationService

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        """
        Register a new user and create their organization.

        Raises:
            ConflictError: If email already exists.
        """
        # Check email uniqueness
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ConflictError(f"Email '{data.email}' is already registered")

        # Create organization first
        org_service = OrganizationService(self.db)
        org = await org_service.create_org_internal(
            name=data.organization_name,
            owner_id=None,  # Will be set after user creation
        )

        # Create user
        user = await self.user_repo.create(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role="admin",  # First user of an org is admin
            organization_id=org.id,
            is_active=True,
        )

        # Set org owner_id now that we have the user
        from app.repositories.organization_repository import OrganizationRepository

        org_repo = OrganizationRepository(self.db)
        await org_repo.update(org, owner_id=user.id)

        logger.info("User registered", user_id=str(user.id), email=user.email)
        return await self._issue_tokens(user)

    async def login(self, data: LoginRequest) -> TokenResponse:
        """
        Authenticate user credentials and issue token pair.

        Raises:
            AuthenticationError: If credentials are invalid.
        """
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        logger.info("User logged in", user_id=str(user.id), email=user.email)
        return await self._issue_tokens(user)

    async def refresh(self, raw_token: str) -> TokenResponse:
        """
        Rotate refresh token.

        On valid token: issue new pair, invalidate old token.
        On reused/invalid token: revoke entire session family.

        Raises:
            AuthenticationError: If token is invalid, expired, or reused.
        """
        hashed = hash_refresh_token(raw_token)
        token_record = await self.token_repo.get_by_hash(hashed)

        if not token_record:
            raise AuthenticationError("Invalid refresh token")

        # Reuse detection: token was already revoked → family invalidation
        if token_record.is_revoked:
            logger.warning(
                "Refresh token reuse detected — revoking session family",
                session_id=token_record.session_id,
            )
            await self.token_repo.revoke_session(token_record.session_id)
            raise AuthenticationError("Refresh token already used. Please log in again.")

        # Check expiry
        if token_record.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            await self.token_repo.revoke(token_record)
            raise AuthenticationError("Refresh token has expired")

        # Revoke old token (rotation)
        await self.token_repo.revoke(token_record)

        # Issue new pair
        user = await self.user_repo.get(token_record.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User account not found or deactivated")

        return await self._issue_tokens(user, session_id=token_record.session_id)

    async def logout(self, raw_token: str) -> None:
        """Revoke a specific refresh token."""
        hashed = hash_refresh_token(raw_token)
        token_record = await self.token_repo.get_by_hash(hashed)
        if token_record and not token_record.is_revoked:
            await self.token_repo.revoke(token_record)

    async def get_me(self, user: User) -> UserResponse:
        """Return current user profile."""
        return UserResponse.model_validate(user)

    async def _issue_tokens(self, user: User, session_id: str | None = None) -> TokenResponse:
        """Create access + refresh token pair and persist the refresh token."""
        extra_claims = {
            "role": user.role,
            "org_id": str(user.organization_id) if user.organization_id else None,
        }
        access_token = create_access_token(subject=str(user.id), extra_claims=extra_claims)
        raw_refresh, hashed_refresh = create_refresh_token()

        # Reuse existing session_id or create a new one
        sid = session_id or secrets.token_hex(32)

        await self.token_repo.create_token(
            user_id=user.id,
            hashed_token=hashed_refresh,
            session_id=sid,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )
