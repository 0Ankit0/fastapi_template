from fastapi import APIRouter

from .v1 import auth, ip_access_control, token_management, rbac, users, tenant

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(ip_access_control.router, prefix="/ip-access", tags=["ip-access"])
api_router.include_router(token_management.router, prefix="/tokens", tags=["tokens"])
api_router.include_router(rbac.router, tags=["rbac"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(tenant.router, prefix="/tenants", tags=["tenants"])