from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication"])
from .register import router as register_router
from .token import router as token_router
from .password import router as password_router
from .login import router as login_router

router.include_router(register_router)
router.include_router(token_router)
router.include_router(password_router)
router.include_router(login_router)