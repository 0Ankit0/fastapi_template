from fastapi import APIRouter
from .subscriptions import router as sub_router

subscription_router = APIRouter()
subscription_router.include_router(sub_router)

__all__ = ["subscription_router"]
