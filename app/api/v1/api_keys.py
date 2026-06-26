"""
API Keys router.
"""

import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.api_keys import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse
from app.schemas.common import MessageResponse
from app.services.api_key_service import APIKeyService

router = APIRouter(prefix="/apikeys", tags=["API Keys"])


@router.post("", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(
    data: APIKeyCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> APIKeyCreatedResponse:
    """
    Create a new API key for the current user's organization.

    ⚠️ The full secret is shown **only once** in this response.
    Store it securely — it cannot be retrieved again.
    """
    if not current_user.organization_id:
        from app.core.exceptions import ValidationError

        raise ValidationError("User does not belong to an organization")
    return await APIKeyService(db).create_key(current_user.organization_id, data)


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: CurrentUser,
    db: DBSession,
) -> list[APIKeyResponse]:
    """List all API keys for the current organization (secrets not included)."""
    if not current_user.organization_id:
        return []
    return await APIKeyService(db).list_keys(current_user.organization_id)


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> MessageResponse:
    """Revoke (soft-delete) an API key."""
    if not current_user.organization_id:
        from app.core.exceptions import ValidationError

        raise ValidationError("User does not belong to an organization")
    await APIKeyService(db).revoke_key(key_id, current_user.organization_id)
    return MessageResponse(message="API key revoked")
