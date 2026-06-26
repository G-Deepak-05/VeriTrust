"""API Key repository."""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.models.api_key import APIKey
from app.repositories.base_repository import BaseRepository


class APIKeyRepository(BaseRepository[APIKey]):
    model = APIKey

    async def get_by_hash(self, hashed_secret: str) -> APIKey | None:
        result = await self.db.execute(
            select(APIKey)
            .options(joinedload(APIKey.organization))
            .where(APIKey.hashed_secret == hashed_secret)
        )
        return result.scalar_one_or_none()

    async def get_by_org(self, org_id: UUID) -> list[APIKey]:
        result = await self.db.execute(
            select(APIKey).where(APIKey.organization_id == org_id).order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_last_used(self, key_id: UUID) -> None:
        """Update last_used_at non-blocking (fire and forget style)."""
        await self.db.execute(
            update(APIKey).where(APIKey.id == key_id).values(last_used_at=datetime.now(UTC))
        )
