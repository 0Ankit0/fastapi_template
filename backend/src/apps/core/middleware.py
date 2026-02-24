from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlmodel import select
from src.apps.iam.models.ip_access_control import IPAccessControl, IpAccessStatus
from src.apps.iam.models.user import User
from src.apps.core import security
from src.apps.core.security import TokenType
from src.apps.core.cache import RedisCache
from src.apps.core.config import settings
from src.db.session import get_session
from datetime import datetime

_IP_STATUS_TTL = 300  # 5 minutes

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


class IPAccessControlMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS = [
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for excluded paths (docs only)
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)

        ip_address = request.client.host if request.client else None
        if not ip_address:
            return await call_next(request)

        # Extract token from Authorization header or cookie
        auth_header = request.headers.get("Authorization")
        cookie_token = request.cookies.get("access_token")
        token = None

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        elif cookie_token:
            token = cookie_token

        if not token:
            return await call_next(request)

        try:
            payload = security.verify_token(token, token_type=TokenType.ACCESS)
            user_id = payload.get("sub")
            if not payload or not user_id:
                return await call_next(request)

            # --- Token-IP binding (production only) ---
            # Each access token carries the IP it was issued for as the "ip" claim.
            # In production, reject requests where the current IP differs from the
            # IP embedded in the token signature.
            if not settings.DEBUG:
                token_ip = payload.get("ip")
                if token_ip and token_ip != ip_address:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Token is not valid for this IP address",
                    )

            # --- IP access control check (Redis-first in production) ---
            cache_key = f"ip_access_status:{user_id}:{ip_address}"

            cached = await RedisCache.get(cache_key)
            if cached is not None:
                cached_status = cached.get("status")
                if cached_status == IpAccessStatus.BLACKLISTED:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your IP address has been blacklisted",
                    )
                if cached_status == IpAccessStatus.PENDING:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access from this IP is pending approval. Please check your email or notifications.",
                    )
                # WHITELISTED → allow through without a DB round-trip
                return await call_next(request)

            # Cache miss → query database
            async for db in get_session():
                try:
                    result = await db.execute(
                        select(IPAccessControl).where(
                            IPAccessControl.user_id == int(user_id),
                            IPAccessControl.ip_address == ip_address,
                        )
                    )
                    ip_control = result.scalars().first()

                    if ip_control:
                        # Populate cache for future requests
                        await RedisCache.set(
                            cache_key, {"status": ip_control.status}, ttl=_IP_STATUS_TTL
                        )

                        if ip_control.status == IpAccessStatus.BLACKLISTED:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Your IP address has been blacklisted",
                            )
                        elif ip_control.status == IpAccessStatus.PENDING:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Access from this IP is pending approval. Please check your email or notifications.",
                            )
                        elif ip_control.status == IpAccessStatus.WHITELISTED:
                            ip_control.last_seen = datetime.now()
                            await db.commit()
                            return await call_next(request)
                    else:
                        # New IP detected — create a pending entry
                        new_ip_control = IPAccessControl(
                            user_id=int(user_id),
                            ip_address=ip_address,
                            status=IpAccessStatus.PENDING,
                            reason="New IP detected",
                            last_seen=datetime.now(),
                        )
                        db.add(new_ip_control)
                        await db.commit()

                        # Cache the pending status
                        await RedisCache.set(
                            cache_key,
                            {"status": IpAccessStatus.PENDING},
                            ttl=_IP_STATUS_TTL,
                        )

                        # Fetch user to send notification email
                        user_result = await db.execute(
                            select(User).where(User.id == int(user_id))
                        )
                        user_obj = user_result.scalars().first()

                        if user_obj:
                            whitelist_token = security.create_ip_action_token(
                                int(user_id), ip_address, "whitelist"
                            )
                            blacklist_token = security.create_ip_action_token(
                                int(user_id), ip_address, "blacklist"
                            )
                            from src.apps.iam.services.email import EmailService
                            await EmailService.send_new_ip_notification(
                                user_obj, ip_address, whitelist_token, blacklist_token
                            )

                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="New IP detected. Please check your email to approve this IP address.",
                        )
                finally:
                    await db.close()

                break

        except HTTPException:
            raise
        except Exception:
            # On unexpected errors allow the request through to avoid blocking
            # legitimate users due to transient failures.
            return await call_next(request)

        return await call_next(request)

