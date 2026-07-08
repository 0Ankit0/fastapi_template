from fastapi import APIRouter

def load_all_models() -> None:
    """Import all models to ensure they are registered with SQLAlchemy metadata."""
    from .iam.models import User, UserProfile, TokenTracking, LoginAttempt, UsedToken
    from .organizations.models import Organization
    from .notification.models import Notification, NotificationPreference

def get_all_routers() -> APIRouter:
    """Return a list of all API routers from the apps."""
    from .iam.api.v1 import get_all_iam_routers
    from .notification.api.v1 import get_all_notification_routers
    from .organizations.api.v1 import get_all_organization_routers
    from .realtime.api import sse_router, websocket_router

    router = APIRouter()
    router.include_router(get_all_iam_routers())
    router.include_router(get_all_notification_routers())
    router.include_router(get_all_organization_routers())
    router.include_router(websocket_router)
    router.include_router(sse_router)

    return router