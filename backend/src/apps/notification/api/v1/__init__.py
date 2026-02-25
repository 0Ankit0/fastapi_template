from fastapi import APIRouter

from .notifications import router as notifications_router
from .notification_preferences import router as preferences_router

router = APIRouter()
router.include_router(notifications_router)
router.include_router(preferences_router)
