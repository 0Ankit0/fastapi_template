from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from src.apps.core.config import settings
from src.apps.core.handler import rate_limit_exceeded_handler
from src.apps.core.middleware import SecurityHeadersMiddleware, IPAccessControlMiddleware
from src.apps.iam.api import api_router
from src.db.session import engine
from src.apps.iam.casbin_enforcer import CasbinEnforcer
from src.apps.core.cache import RedisCache

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Casbin enforcer and Redis cache on startup"""
    enforcer = await CasbinEnforcer.get_enforcer(engine)
    app.state.casbin_enforcer = enforcer
    
    # Initialize Redis cache in production
    if not settings.DEBUG:
        await RedisCache.get_client()
    
    yield
    
    # Cleanup Redis connection on shutdown
    await RedisCache.close()

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

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# IP access control middleware
app.add_middleware(IPAccessControlMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware (prevent host header attacks)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", settings.SERVER_HOST.replace("http://", "").replace("https://", "")]
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", include_in_schema=False)
async def read_root() -> RedirectResponse:
    """Redirect root to the interactive API documentation."""
    return RedirectResponse(url="/docs")