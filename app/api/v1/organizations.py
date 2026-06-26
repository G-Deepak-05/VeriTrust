"""
Organizations router.
"""

import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.common import MessageResponse
from app.schemas.organizations import OrgCreate, OrgResponse, OrgUpdate
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrgResponse, status_code=201)
async def create_organization(
    data: OrgCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> OrgResponse:
    """Create a new organization. Caller becomes the owner."""
    return await OrganizationService(db).create_org(data, owner_id=current_user.id)


@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> OrgResponse:
    return await OrganizationService(db).get_org(org_id)


@router.put("/{org_id}", response_model=OrgResponse)
async def update_organization(
    org_id: uuid.UUID,
    data: OrgUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> OrgResponse:
    return await OrganizationService(db).update_org(org_id, data, requester_id=current_user.id)


@router.delete("/{org_id}", response_model=MessageResponse)
async def deactivate_organization(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    await OrganizationService(db).deactivate_org(org_id, requester_id=current_user.id)
    return MessageResponse(message="Organization deactivated")
