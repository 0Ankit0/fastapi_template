from fastapi import APIRouter
from . import login, signup, password, token, otp

__all__ = ["router", "login", "signup", "password", "token", "otp"]

router = APIRouter()

# Include all sub-routers
router.include_router(login.router, tags=["auth-login"])
router.include_router(signup.router, tags=["auth-signup"])
router.include_router(password.router, tags=["auth-password"])
router.include_router(token.router, tags=["auth-token"])
router.include_router(otp.router, tags=["auth-otp"])
