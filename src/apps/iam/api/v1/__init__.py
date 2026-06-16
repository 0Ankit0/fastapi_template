from fastapi import APIRouter

def get_all_iam_routers() -> APIRouter:
    """Return a list of all API routers from the apps."""
    from .auth import router as auth_router
    from .users import router as users_router
    from .casbin import router as casbin_router
    from .token_management import router as token_management_router

    router = APIRouter(prefix="/api/v1")
    router.include_router(auth_router)
    router.include_router(users_router)
    router.include_router(casbin_router)
    router.include_router(token_management_router)

    return router