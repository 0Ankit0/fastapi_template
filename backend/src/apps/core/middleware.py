from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt, JWTError
import re


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # CSP with allowances for Swagger UI
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
            "font-src 'self' data:; "
            "connect-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


# Routes that require both a valid JWT *and* an active subscription.
# Any path matching one of these prefixes will be checked.
_SUBSCRIPTION_PROTECTED_PREFIXES = (
    "/api/v1/tenants",
)

# Sub-paths exempt from the subscription check even if under a protected prefix.
_SUBSCRIPTION_EXEMPT_PATTERNS: list[re.Pattern[str]] = []


class SubscriptionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces:
    1. A valid, non-expired JWT access token in the Authorization header or
       the ``access_token`` cookie.
    2. An active ``OwnerSubscription`` for the authenticated user (superusers
       are always exempt).

    Only requests whose paths begin with one of ``_SUBSCRIPTION_PROTECTED_PREFIXES``
    are checked.  All other paths pass through untouched.

    Returns:
        401 – token missing, malformed, or expired.
        402 – token valid but subscription is inactive / expired.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Fast path: only inspect subscription-protected routes.
        if not any(path.startswith(prefix) for prefix in _SUBSCRIPTION_PROTECTED_PREFIXES):
            return await call_next(request)

        # Allow explicitly exempt sub-paths.
        if any(p.search(path) for p in _SUBSCRIPTION_EXEMPT_PATTERNS):
            return await call_next(request)

        # ── 1. Extract and validate the JWT ──────────────────────────────────
        token: str | None = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
        if not token:
            from src.apps.core.config import settings as _settings
            token = request.cookies.get(_settings.ACCESS_TOKEN_COOKIE)

        if not token:
            return JSONResponse(
                status_code=401,
                content={"code": "not_authenticated", "message": "Authentication token is missing."},
            )

        try:
            from src.apps.core.config import settings as _settings
            from src.apps.core import security as _security
            payload = jwt.decode(token, _settings.SECRET_KEY, algorithms=[_security.ALGORITHM])
        except JWTError:
            return JSONResponse(
                status_code=401,
                content={"code": "invalid_token", "message": "Authentication token is invalid or expired."},
            )

        token_type = payload.get("type", "")
        if token_type not in ("access", "bearer"):
            return JSONResponse(
                status_code=401,
                content={"code": "invalid_token_type", "message": "Invalid token type."},
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            return JSONResponse(
                status_code=401,
                content={"code": "invalid_token", "message": "Token subject missing."},
            )

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=401,
                content={"code": "invalid_token", "message": "Token subject invalid."},
            )

        # ── 2. Check subscription validity ───────────────────────────────────
        from src.db.session import async_session_factory
        from src.apps.iam.models.user import User as _User
        from src.apps.subscription.services.subscription_service import (
            get_subscription as _get_sub,
            is_subscription_active as _is_active,
        )
        from sqlmodel import select as _select

        async with async_session_factory() as db:
            result = await db.execute(_select(_User).where(_User.id == user_id))
            user = result.scalars().first()

            if user is None:
                return JSONResponse(
                    status_code=401,
                    content={"code": "user_not_found", "message": "User not found."},
                )

            # Superusers bypass subscription checks.
            if user.is_superuser:
                return await call_next(request)

            sub = await _get_sub(db, user_id)
            if not _is_active(sub):
                return JSONResponse(
                    status_code=402,
                    content={
                        "code": "subscription_required",
                        "message": (
                            "Your subscription has expired or is not active. "
                            "Please subscribe or renew to access this feature."
                        ),
                        "subscription_status": sub.status.value if sub else "none",
                    },
                )

        return await call_next(request)
