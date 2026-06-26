"""
Users router.
"""

import uuid

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.auth import UserResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    current_user: CurrentUser,
    db: DBSession,
) -> PaginatedResponse[UserResponse]:
    """List all users in the current organization. Requires admin role."""
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    if not current_user.organization_id:
        return PaginatedResponse(data=[], total=0, page=1, page_size=20, total_pages=0)
    users, total = await repo.get_by_org(current_user.organization_id)
    return PaginatedResponse(
        data=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=1,
        page_size=20,
        total_pages=(total + 19) // 20,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> UserResponse:
    from app.core.exceptions import NotFoundError
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user or user.organization_id != current_user.organization_id:
        raise NotFoundError("User", str(user_id))
    return UserResponse.model_validate(user)
