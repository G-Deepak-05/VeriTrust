"""
Authentication router.
"""

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DBSession
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: DBSession) -> TokenResponse:
    """Register a new user and organization. Returns token pair."""
    return await AuthService(db).register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: DBSession) -> TokenResponse:
    """Authenticate and receive access + refresh tokens."""
    return await AuthService(db).login(data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: DBSession) -> TokenResponse:
    """Rotate refresh token — issues new access + refresh pair."""
    return await AuthService(db).refresh(data.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(data: RefreshRequest, db: DBSession) -> MessageResponse:
    """Revoke a refresh token to end the session."""
    await AuthService(db).logout(data.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser, db: DBSession) -> UserResponse:
    """Return the currently authenticated user's profile."""
    return await AuthService(db).get_me(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest, db: DBSession) -> MessageResponse:
    """Send a password reset email via Mailpit."""
    # TODO: implement email dispatch via Celery task
    return MessageResponse(message="If that email exists, a reset link has been sent.")
