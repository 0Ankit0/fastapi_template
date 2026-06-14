from .organization_members import router as organization_members_router
from .organization import router as organizations_router
from fastapi import APIRouter

def get_all_organization_routers() -> APIRouter:
    router = APIRouter(prefix="/v1")
    router.include_router(organizations_router, prefix="/organizations", tags=["organizations"])
    router.include_router(organization_members_router, prefix="/organization-members", tags=["organization-members"])
    return router
