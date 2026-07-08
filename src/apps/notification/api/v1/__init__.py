from fastapi import APIRouter

from .notification_preferences import router as notification_preferences_router
from .notifications import router as notifications_router


def get_all_notification_routers() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(notifications_router)
    router.include_router(notification_preferences_router)
    return router
