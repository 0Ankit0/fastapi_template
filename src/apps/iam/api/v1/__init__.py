from fastapi import APIRouter

def get_all_iam_routers() -> APIRouter:
    """Return a list of all API routers from the apps."""
    from .auth import router as auth_router

    router = APIRouter(prefix="/api/v1")
    router.include_router(auth_router)

    return router