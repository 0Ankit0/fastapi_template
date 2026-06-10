from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication"])

from . import login, logout, refresh, password_reset, email_verification, temp_auth

router.include_router(login.router)
router.include_router(logout.router)
router.include_router(refresh.router)
router.include_router(password_reset.router)
router.include_router(email_verification.router)
router.include_router(temp_auth.router)