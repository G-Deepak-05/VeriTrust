"""Refresh token repository with rotation and reuse detection support."""
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.repositories.base_repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def create_token(self, user_id: UUID, hashed_token: str, session_id: str) -> RefreshToken:
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        return await self.create(
            user_id=user_id,
            hashed_token=hashed_token,
            session_id=session_id,
            expires_at=expires_at,
            is_revoked=False,
        )

    async def get_by_hash(self, hashed_token: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        await self.update(token, is_revoked=True)

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Revoke all active tokens for a user (reuse-detection family invalidation)."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)  # noqa: E712
            .values(is_revoked=True)
        )

    async def revoke_session(self, session_id: str) -> None:
        """Revoke all tokens belonging to a session family."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.session_id == session_id)
            .values(is_revoked=True)
        )
