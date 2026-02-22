from fastapi import APIRouter

from .v1 import auth, ip_access_control, token_management

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(ip_access_control.router, prefix="/ip-access", tags=["ip-access"])
api_router.include_router(token_management.router, prefix="/tokens", tags=["tokens"])