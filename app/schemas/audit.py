"""
Audit log schemas.
"""
from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema


class AuditLogResponse(BaseSchema):
    id: UUID
    organization_id: UUID | None = None
    actor_id: UUID | None = None
    actor_email: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    endpoint: str | None = None
    method: str | None = None
    ip_address: str | None = None
    status: str
    metadata_: dict = {}
    created_at: datetime
