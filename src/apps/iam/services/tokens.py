from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response, status

from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User
from src.apps.iam.repositories import iam_repository
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.token_tracking import TokenTrackingResponse
from src.apps.iam.utils.ip_access import get_client_ip, revoke_tokens_for_ip
from src.core import security
from src.core.cache import RedisCache
from src.core.config import settings
from src.core.cookies import clear_auth_cookies, set_auth_cookies
from src.core.enums import UserStatus
from src.core.exceptions import AuthorizationError
from src.core.pagination import (
    CursorSortDirection,
    apply_datetime_id_cursor_filter,
    apply_ordering,
    build_datetime_id_cursor,
    to_cursor_page,
)
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination
from src.core.security import TokenType
from src.db.query import select


class TokenService:
    async def list_active_tokens(
        self,
        db,
        *,
        current_user: User,
        pagination: CursorPagination,
        sort_direction: CursorSortDirection,
    ) -> CursorPage[TokenTrackingResponse]:
        """Return paginated active sessions for the current user."""
        def apply_filter(query):
            """Apply cursor filters to the active-token query."""
            return apply_datetime_id_cursor_filter(
                query,
                pagination,
                datetime_column=TokenTracking.created_at,
                id_column=TokenTracking.id,
                direction=sort_direction,
            )
        
        def apply_order(query):
            """Apply stable ordering for active-token pagination."""
            return apply_ordering(
                query,
                order_column=TokenTracking.created_at,
                id_column=TokenTracking.id,
                direction=sort_direction,
            )
        
        rows = await iam_repository.list_active_tokens_paginated(
            db,
            current_user.id,
            apply_filter,
            apply_order,
            pagination.limit + 1,
        )
        return to_cursor_page(
            rows,
            pagination,
            serializer=TokenTrackingResponse.model_validate,
            next_cursor_builder=build_datetime_id_cursor,
        )

    async def revoke_token(self, db, *, token_id: int, current_user: User) -> ApiSuccessResponse[None]:
        """Revoke one active session token by id for the current user."""
        token_tracking = await iam_repository.get_token_tracking_by_id(db, token_id, current_user.id)
        if not token_tracking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
        if not token_tracking.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token is already revoked")

        await iam_repository.revoke_token(
            db,
            token_tracking=token_tracking,
            reason="Revoked by user",
        )
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
        return ApiSuccessResponse[None](message="Token revoked successfully", data=None)

    async def revoke_all_tokens(self, db, *, current_user: User) -> ApiSuccessResponse[dict[str, int]]:
        """Revoke every active session token for the current user."""
        tokens = await iam_repository.list_active_tokens(db, current_user.id)
        revoked_count = await iam_repository.revoke_tokens(
            db,
            tokens=tokens,
            reason="All tokens revoked by user",
        )
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
        return ApiSuccessResponse[dict[str, int]](
            message=f"Revoked {revoked_count} active token(s)",
            data={"revoked": revoked_count},
        )

    async def token_insights(self, db, *, current_user: User) -> ApiSuccessResponse[dict[str, int]]:
        """Return aggregate token metrics for the current user."""
        now = datetime.now(timezone.utc)
        next_24h = now.replace(microsecond=0) + timedelta(hours=24)

        active = await iam_repository.count_tokens(db, user_id=current_user.id, is_active=True)
        revoked = await iam_repository.count_tokens(db, user_id=current_user.id, is_active=False)
        expiring_24h = await iam_repository.count_tokens(
            db,
            user_id=current_user.id,
            is_active=True,
            expires_before=next_24h,
            expires_after=now,
        )
        return ApiSuccessResponse[dict[str, int]](
            message="Token insights fetched successfully",
            data={
                "active": int(active),
                "revoked": int(revoked),
                "expiring_24h": int(expiring_24h),
            },
        )

    async def refresh_token(
        self,
        db,
        *,
        response: Response,
        request: Request,
        refresh_token: str | None,
        set_cookie: bool,
    ) -> ApiSuccessResponse[Token] | ApiSuccessResponse[None]:
        """Validate refresh token and rotate access/refresh credentials."""
        if not refresh_token:
            refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if not refresh_token:
            raise AuthorizationError("Refresh token is required")

        payload = security.verify_token(refresh_token, token_type=TokenType.REFRESH)
        user_id_raw = payload.get("sub") if payload else None
        if not payload or not user_id_raw:
            raise AuthorizationError("Invalid refresh token")

        user_id = int(user_id_raw)
        refresh_payload = security.decode_token(refresh_token)
        refresh_jti = refresh_payload.get("jti")
        token_tracking = None
        if refresh_jti:
            token_tracking = await iam_repository.get_active_refresh_tracking_by_jti(db, refresh_jti)
            if not token_tracking:
                raise AuthorizationError("Token has been revoked or is invalid")

        user = await iam_repository.get_user_by_id(db, user_id)
        if not user or user.status != UserStatus.ACTIVE:
            raise AuthorizationError("User not found or inactive")

        ip_address = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")

        if refresh_jti and token_tracking:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = "Token refreshed"

        access_token = security.create_access_token(
            user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        new_refresh_token = security.create_refresh_token(user.id)

        access_payload = security.decode_token(access_token)
        new_refresh_payload = security.decode_token(new_refresh_token)

        await revoke_tokens_for_ip(db, user.id, ip_address)

        await iam_repository.create_token_tracking(
            db,
            user_id=user.id,
            token_jti=access_payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(access_payload),
        )
        await iam_repository.create_token_tracking(
            db,
            user_id=user.id,
            token_jti=new_refresh_payload["jti"],
            token_type=TokenType.REFRESH,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(new_refresh_payload),
        )
        await iam_repository.commit(db)
        await RedisCache.clear_pattern(f"tokens:active:{user_id}:*")

        if set_cookie:
            set_auth_cookies(response, access_token=access_token, refresh_token=new_refresh_token)
            return ApiSuccessResponse[None](message="Token refreshed successfully")

        return ApiSuccessResponse[Token](
            message="Token refreshed successfully",
            data=Token(access=access_token, refresh=new_refresh_token, token_type=TokenType.BEARER.value),
        )

    async def logout(self, db, *, request: Request, response: Response, current_user: User) -> dict[str, str]:
        """Revoke current-device sessions and clear auth cookies."""
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)

        if token:
            try:
                payload = security.decode_token(token)
                jti = payload.get("jti")
                ip_address = get_client_ip(request)
                if jti:
                    tokens = await iam_repository.list_active_tokens(db, current_user.id)
                    tokens_for_ip = [t for t in tokens if t.ip_address == ip_address]
                    await iam_repository.revoke_tokens(
                        db,
                        tokens=tokens_for_ip,
                        reason="User logout from this device",
                    )
                    await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
            except Exception:
                pass

        clear_auth_cookies(response)
        return {"message": "Successfully logged out from this device"}


token_service = TokenService()
