from .organization_members import router as organization_members_router
from .organization import router as organizations_router
from .public_urls import router as public_router
from fastapi import APIRouter

def get_all_organization_routers() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(organizations_router)
    router.include_router(organization_members_router)
    router.include_router(public_router)    
    return router
