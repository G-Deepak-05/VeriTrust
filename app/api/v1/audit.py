"""
Audit logs router.
"""
from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DBSession
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> PaginatedResponse[AuditLogResponse]:
    """List audit events for the current organization. Requires admin role."""
    if not current_user.organization_id:
        return PaginatedResponse(data=[], total=0, page=1, page_size=page_size, total_pages=0)

    repo = AuditLogRepository(db)
    offset = (page - 1) * page_size
    items, total = await repo.get_by_org(
        current_user.organization_id, offset=offset, limit=page_size
    )
    return PaginatedResponse(
        data=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
