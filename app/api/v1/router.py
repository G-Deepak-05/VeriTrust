"""
Central API v1 router — aggregates all sub-routers.
"""

from fastapi import APIRouter

from app.api.v1 import (
    api_keys,
    audit,
    auth,
    dashboard,
    fraud,
    health,
    organizations,
    users,
    verification,
)

router = APIRouter()

router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(users.router)
router.include_router(api_keys.router)
router.include_router(verification.router)
router.include_router(fraud.router)
router.include_router(dashboard.router)
router.include_router(audit.router)
router.include_router(health.router)
