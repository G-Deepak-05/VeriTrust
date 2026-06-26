"""Audit log repository."""

from uuid import UUID

from app.models.audit_log import AuditLog
from app.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def get_by_org(
        self, org_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[AuditLog], int]:
        return await self.get_multi(
            filters=[AuditLog.organization_id == org_id],
            offset=offset,
            limit=limit,
        )

    async def get_by_actor(
        self, actor_id: UUID, offset: int = 0, limit: int = 50
    ) -> tuple[list[AuditLog], int]:
        return await self.get_multi(
            filters=[AuditLog.actor_id == actor_id],
            offset=offset,
            limit=limit,
        )
