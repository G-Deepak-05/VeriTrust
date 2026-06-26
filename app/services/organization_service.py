"""
Organization service — CRUD and member management.
"""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organizations import OrgCreate, OrgResponse, OrgUpdate

logger = get_logger(__name__)


def _slugify(name: str) -> str:
    """Convert organization name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = OrganizationRepository(db)

    async def create_org(self, data: OrgCreate, owner_id: uuid.UUID) -> OrgResponse:
        base_slug = _slugify(data.name)
        slug = await self._unique_slug(base_slug)

        org = await self.repo.create(
            name=data.name,
            slug=slug,
            description=data.description,
            website=data.website,
            owner_id=owner_id,
        )
        logger.info("Organization created", org_id=str(org.id), slug=org.slug)
        return OrgResponse.model_validate(org)

    async def create_org_internal(self, name: str, owner_id: uuid.UUID | None):
        """Called during registration before user exists."""
        base_slug = _slugify(name)
        slug = await self._unique_slug(base_slug)
        return await self.repo.create(
            name=name,
            slug=slug,
            owner_id=owner_id or uuid.uuid4(),  # Placeholder, updated after user creation
        )

    async def get_org(self, org_id: uuid.UUID) -> OrgResponse:
        org = await self.repo.get(org_id)
        if not org:
            raise NotFoundError("Organization", str(org_id))
        return OrgResponse.model_validate(org)

    async def update_org(
        self, org_id: uuid.UUID, data: OrgUpdate, requester_id: uuid.UUID
    ) -> OrgResponse:
        org = await self.repo.get(org_id)
        if not org:
            raise NotFoundError("Organization", str(org_id))
        if org.owner_id != requester_id:
            from app.core.exceptions import InsufficientPermissionsError

            raise InsufficientPermissionsError("Only the org owner can update the organization")

        updates = data.model_dump(exclude_none=True)
        org = await self.repo.update(org, **updates)
        return OrgResponse.model_validate(org)

    async def deactivate_org(self, org_id: uuid.UUID, requester_id: uuid.UUID) -> None:
        org = await self.repo.get(org_id)
        if not org:
            raise NotFoundError("Organization", str(org_id))
        await self.repo.update(org, is_active=False)
        logger.info("Organization deactivated", org_id=str(org_id))

    async def _unique_slug(self, base: str) -> str:
        """Ensure slug uniqueness by appending a suffix if needed."""
        slug = base
        suffix = 1
        while await self.repo.get_by_slug(slug):
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug
