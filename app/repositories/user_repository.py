"""User repository."""

from uuid import UUID

from sqlalchemy import select

from app.models.user import User
from app.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_org(
        self, org_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[User], int]:
        return await self.get_multi(
            filters=[User.organization_id == org_id],
            offset=offset,
            limit=limit,
        )
