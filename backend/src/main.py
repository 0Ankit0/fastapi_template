from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from src.apps.core.config import settings
from src.apps.core.handler import rate_limit_exceeded_handler
from src.apps.core.middleware import SecurityHeadersMiddleware
# IAM GraphQL routers
from src.apps.iam.api.v1.users import graphql_router as users_graphql_router
from src.apps.iam.api.v1.token_management import graphql_router as token_management_graphql_router
from src.apps.iam.api.v1.auth.password import graphql_router as password_graphql_router
from src.apps.iam.api.v1.auth.otp import graphql_router as otp_graphql_router
from src.apps.iam.api.v1.auth.login import graphql_router as login_graphql_router
from src.apps.iam.api.v1.auth.signup import graphql_router as signup_graphql_router
from src.apps.finance.api.v1.payment import graphql_router as finance_graphql_router
from src.apps.multitenancy.api.v1.tenant_graphql import graphql_router as multitenancy_graphql_router
from src.db.session import engine, init_db
from src.apps.iam.casbin_enforcer import CasbinEnforcer
from src.apps.websocket.api import ws_router
from src.apps.websocket.api.v1.ws_graphql import graphql_router as ws_graphql_router
from src.apps.websocket.manager import manager as ws_manager
from src.apps.core.cache import RedisCache
from src.apps.notification.api.v1.notifications import graphql_router as notification_graphql_router
from src.apps.analytics import init_analytics, shutdown_analytics
from src.apps.analytics.api import graphql_router as analytics_graphql_router
from src.apps.analytics.middleware import AnalyticsMiddleware

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables, Casbin enforcer, Redis cache, WebSocket manager, and Analytics on startup."""
    await init_db()

    enforcer = await CasbinEnforcer.get_enforcer(engine)
    app.state.casbin_enforcer = enforcer

    # Initialize Redis cache + WebSocket pub/sub in production
    if not settings.DEBUG:
        if settings.REDIS_URL:
            await RedisCache.get_client()
            await ws_manager.setup_redis(settings.REDIS_URL)

    app.state.ws_manager = ws_manager

    # Analytics service (no-op when ANALYTICS_ENABLED=false)
    app.state.analytics = init_analytics()

    yield

    # Cleanup on shutdown
    await ws_manager.teardown()
    await RedisCache.close()
    await shutdown_analytics()

app = FastAPI(
    lifespan=lifespan,
    title="fastapi_template",
    description="A template for FastAPI applications",
    version="0.1.0",
    swagger_ui_parameters={
        "syntaxHighlight.theme": "monokai",  # Syntax highlighting theme
        "deepLinking": True,  # Enable deep linking to operations
        "displayOperationId": True,  # Show operation IDs
        "filter": True,  # Enable search/filter bar
        "showExtensions": True,  # Show vendor extensions
        "showCommonExtensions": True,
        "persistAuthorization": True,  # Remember authorization between reloads
        "displayRequestDuration": True,  # Show request duration
        "docExpansion": "list",  # Default expansion: "list", "full", or "none"
        "defaultModelsExpandDepth": 1,  # How deep to expand models
        "defaultModelExpandDepth": 1,
    }
)

# Add rate limiter to app state and register exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler) 

# Trust proxy headers (X-Forwarded-For / X-Real-IP) so request.client.host
# reflects the real client IP rather than the loopback / proxy address.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Analytics request-tracking middleware
app.add_middleware(AnalyticsMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=not settings.DEBUG,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (prevent host header attacks)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.SERVER_HOST.replace("http://", "").replace("https://", "")]
    )

# app.include_router(api_router, prefix=settings.API_V1_STR)  # REST IAM router removed
app.include_router(finance_graphql_router, prefix="/graphql/finance")
app.include_router(multitenancy_graphql_router, prefix="/graphql/tenants")
app.include_router(ws_router, prefix=settings.API_V1_STR)
app.include_router(ws_graphql_router, prefix="/graphql/ws")
app.include_router(analytics_graphql_router, prefix="/graphql/analytics")

# GraphQL endpoints
app.include_router(notification_graphql_router, prefix="/graphql/notifications")
# IAM GraphQL endpoints
app.include_router(users_graphql_router, prefix="/graphql/users")
app.include_router(token_management_graphql_router, prefix="/graphql/tokens")
app.include_router(password_graphql_router, prefix="/graphql/password")
app.include_router(otp_graphql_router, prefix="/graphql/otp")
app.include_router(login_graphql_router, prefix="/graphql/auth")
app.include_router(signup_graphql_router, prefix="/graphql/auth")

# Serve uploaded media files (avatars, etc.)
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
app.mount(settings.MEDIA_URL, StaticFiles(directory=settings.MEDIA_DIR), name="media")

@app.get("/", include_in_schema=False)
async def read_root() -> RedirectResponse:
    """Redirect root to the interactive API documentation."""
    return RedirectResponse(url="/docs")