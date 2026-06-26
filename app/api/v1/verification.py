"""
Verification router — submit and query verification requests.
"""
import uuid

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DBSession, RedisClient, get_api_key_org
from app.models.organization import Organization
from app.schemas.common import PaginatedResponse
from app.schemas.verification import (
    VerificationDetailResponse,
    VerificationHistoryItem,
    VerificationInput,
    VerificationResponse,
)
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.post("", response_model=VerificationResponse, status_code=201)
async def submit_verification(
    data: VerificationInput,
    db: DBSession,
    redis: RedisClient,
    org: Organization = Depends(get_api_key_org),
) -> VerificationResponse:
    """
    Submit a verification request.

    **Authentication**: Requires `X-Api-Key` header (organization API key).

    Runs the full fraud pipeline and returns a risk score + decision.
    """
    svc = VerificationService(db, redis)
    return await svc.submit(org.id, data)


@router.get("/history", response_model=PaginatedResponse[VerificationHistoryItem])
async def verification_history(
    db: DBSession,
    redis: RedisClient,
    org: Organization = Depends(get_api_key_org),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[VerificationHistoryItem]:
    """List verification history for the organization."""
    svc = VerificationService(db, redis)
    items, total = await svc.get_history(org.id, page=page, page_size=page_size)
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{verification_id}", response_model=VerificationDetailResponse)
async def get_verification(
    verification_id: uuid.UUID,
    db: DBSession,
    redis: RedisClient,
    org: Organization = Depends(get_api_key_org),
) -> VerificationDetailResponse:
    """Get detailed result for a specific verification request."""
    svc = VerificationService(db, redis)
    return await svc.get_verification(verification_id, org.id)
