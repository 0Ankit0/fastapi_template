from fastapi import APIRouter

from src.apps.communications import get_communications_service
from src.apps.core.config import settings

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/capabilities/")
async def get_capabilities() -> dict:
    return get_communications_service().get_capabilities().model_dump()


@router.get("/providers/")
async def get_providers() -> dict:
    return {
        "providers": [
            status.model_dump()
            for status in get_communications_service().get_provider_statuses()
        ]
    }


@router.get("/health/")
async def health() -> dict:
    return {"status": "ok", "service": settings.PROJECT_NAME}


@router.get("/ready/")
async def ready() -> dict:
    return {"ready": True, "project": settings.PROJECT_NAME}
