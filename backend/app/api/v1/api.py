from app.api.v1.endpoints import auth, users, tenants, content, finances, integrations, notifications, webhooks

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(finances.router, prefix="/finances", tags=["finances"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
# Webhooks (often raw processing, but putting under /api/v1/webhooks for consistency or separate?)
# Usually webhooks are root level or specific. Let's put under /api/v1/webhooks for now.
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])

from app.api.v1.endpoints import social_auth
api_router.include_router(social_auth.router, prefix="/social", tags=["social"])
