from fastapi import APIRouter

def load_all_models() -> None:
    """Import all models to ensure they are registered with SQLAlchemy metadata."""
    from .iam.models import User, UserProfile, TokenTracking, LoginAttempt, UsedToken
    from .organizations.models import Organization

def get_all_routers() -> APIRouter:
    """Return a list of all API routers from the apps."""
    from .iam.api.v1 import get_all_iam_routers
    from .organizations.api.v1 import get_all_organization_routers
    from .websockets.api import router as websocket_router

    router = APIRouter()
    router.include_router(get_all_iam_routers())
    router.include_router(get_all_organization_routers())
    router.include_router(websocket_router)

    return router