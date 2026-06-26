"""
API Key service — generation, listing, and revocation.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.security import create_api_key_secret
from app.repositories.api_key_repository import APIKeyRepository
from app.schemas.api_keys import APIKeyCreate, APIKeyCreatedResponse, APIKeyResponse

logger = get_logger(__name__)


class APIKeyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = APIKeyRepository(db)

    async def create_key(self, org_id: uuid.UUID, data: APIKeyCreate) -> APIKeyCreatedResponse:
        """
        Generate a new API key for an organization.
        The full secret is returned ONCE and never stored in plaintext.
        """
        full_key, hashed_secret = create_api_key_secret()
        key_prefix = full_key[:12]  # "vt_live_xxx" — safe to store/display

        api_key = await self.repo.create(
            organization_id=org_id,
            name=data.name,
            key_prefix=key_prefix,
            hashed_secret=hashed_secret,
            permissions=data.permissions,
        )

        logger.info("API key created", key_id=str(api_key.id), org_id=str(org_id))
        return APIKeyCreatedResponse(
            id=api_key.id,
            name=api_key.name,
            key=full_key,
            key_prefix=key_prefix,
            created_at=api_key.created_at,
        )

    async def list_keys(self, org_id: uuid.UUID) -> list[APIKeyResponse]:
        """List all API keys for an org (without secrets)."""
        keys = await self.repo.get_by_org(org_id)
        return [APIKeyResponse.model_validate(k) for k in keys]

    async def revoke_key(self, key_id: uuid.UUID, org_id: uuid.UUID) -> None:
        """Revoke (soft-delete) an API key."""
        api_key = await self.repo.get(key_id)
        if not api_key or api_key.organization_id != org_id:
            raise NotFoundError("API Key", str(key_id))

        await self.repo.update(api_key, is_active=False)
        logger.info("API key revoked", key_id=str(key_id), org_id=str(org_id))
