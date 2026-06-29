from datetime import timedelta, datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from src.core.dependencies import DB
from src.core.enums import UserStatus
from src.core.exceptions import AppError, AuthorizationError, RateLimitError, ValidationError
from src.core.schemas import ApiSuccessResponse
from src.db.query import col, select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings
from src.core import security
from src.core.security import TokenType
from src.core.cache import RedisCache
from src.core.cookies import clear_auth_cookies, set_auth_cookies
from src.core.dependencies import  get_current_user
from src.apps.iam.models.user import User
from src.apps.iam.models import LoginAttempt
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token import  Token
from src.apps.iam.schemas.otp import OtpRequiredResponse
from src.apps.iam.schemas.user import LoginRequest
from src.apps.iam.utils.ip_access import revoke_tokens_for_ip, get_client_ip
from src.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login/", response_model = ApiSuccessResponse[Token] | ApiSuccessResponse[OtpRequiredResponse])
@limiter.limit(lambda: settings.RATE_LIMIT_LOGIN)
async def login_access_token(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: DB,
    set_cookie: bool = False,
) -> ApiSuccessResponse[Token] | ApiSuccessResponse[OtpRequiredResponse]:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    user = None
    
    try:
        result = await db.execute(
            select(User).where(User.username == login_data.username)
        )
        user = result.scalars().first()

        # TODO: Also check for organization access

        if not user:
            login_attempt = LoginAttempt(
                user_id=None,
                ip_address=ip_address,
                attempted_username=login_data.username,
                user_agent=user_agent,
                success=False,
                failure_reason="User not found"
            )
            db.add(login_attempt)
            await db.commit()
            raise ValidationError(
                message="Invalid username or password"
            )

        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_confirmed:
            raise AuthorizationError(
                message="Email verification required. Please check your inbox."
            )

        if settings.MAX_LOGIN_ATTEMPTS > 0 and settings.ACCOUNT_LOCKOUT_DURATION_MINUTES > 0:
            window_start = datetime.now() - timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
            result = await db.execute(
                select(LoginAttempt)
                .where(
                    LoginAttempt.user_id == user.id,
                    LoginAttempt.success == False,
                    LoginAttempt.timestamp >= window_start,
                )
                .order_by(col(LoginAttempt.timestamp).desc())
            )
            failures = result.scalars().all()
            if len(failures) >= settings.MAX_LOGIN_ATTEMPTS:
                last_attempt = failures[0]
                lockout_expires = last_attempt.timestamp + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
                remaining_seconds = int((lockout_expires - datetime.now()).total_seconds())
                if remaining_seconds > 0:
                    remaining_minutes = (remaining_seconds + 59) // 60
                    raise RateLimitError(
                        message=f"Too many failed login attempts. Account locked for {remaining_minutes} more minutes."
                    )

        if not security.verify_password(login_data.password, user.password_hash):
            login_attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=login_data.username,
                user_agent=user_agent,
                success=False,
                failure_reason="Incorrect password"
            )
            db.add(login_attempt)
            await db.commit()
            raise ValidationError(
                message="Invalid username or password"
            )
        
        if not user.status == UserStatus.ACTIVE:
            login_attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=login_data.username,
                user_agent=user_agent,
                success=False,
                failure_reason="User account is inactive"
            )
            db.add(login_attempt)
            await db.commit()
            raise ValidationError(
                message="User account is inactive. Please contact support."
            )
        
        # Check if OTP is enabled for this user
        if user.otp_enabled and user.otp_verified:
            temp_token = security.create_temp_auth_token(user.id, login_data.organization)
            return ApiSuccessResponse[OtpRequiredResponse](
                data=OtpRequiredResponse(
                    requires_otp=True,
                    temp_token=temp_token
                ),
                message="OTP verification required"
            )
        
        # Successful login
        login_attempt = LoginAttempt(
            user_id=user.id,
            ip_address=ip_address,
            attempted_username=login_data.username,
            user_agent=user_agent,
            success=True,
            failure_reason=""
        )
        db.add(login_attempt)
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user.id,login_data.organization, expires_delta=access_token_expires
        )
        refresh_token = security.create_refresh_token(user.id,login_data.organization)
        
        access_payload = security.decode_token(access_token)
        refresh_payload = security.decode_token(refresh_token)

        # Revoke any existing active tokens for this user+IP before issuing new ones
        await revoke_tokens_for_ip(db, user.id, ip_address)

        # Track access token
        access_token_tracking = TokenTracking(
            user_id=user.id,
            token_jti=access_payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(access_payload)
        )
        db.add(access_token_tracking)
        
        # Track refresh token
        refresh_token_tracking = TokenTracking(
            user_id=user.id,
            token_jti=refresh_payload["jti"],
            token_type=TokenType.REFRESH,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(refresh_payload)
        )
        db.add(refresh_token_tracking)
        await db.commit()
        success_login_attempt = LoginAttempt(
            user_id=user.id,
            ip_address=ip_address,
            attempted_username=login_data.username,
            user_agent=user_agent,
            success=True,
            failure_reason=""
        )
        db.add(success_login_attempt)
        await db.commit()
       
        await db.commit()

        if set_cookie:
            set_auth_cookies(
                response,
                access_token=access_token,
                refresh_token=refresh_token,
            )
            return ApiSuccessResponse[Token](
                data=Token(
                    access="",
                    refresh="",
                    token_type=TokenType.BEARER.value
                ),
                message="Logged in successfully"
            )
        
        token_data = Token(
            access=access_token,
            refresh=refresh_token,
            token_type=TokenType.BEARER.value
        )
        return ApiSuccessResponse[Token](
            data=token_data,
            message="Logged in successfully"
        )
    except (HTTPException, AppError):
        await db.rollback()
        raise
    except Exception as ex:
        # await db.rollback()
        logger.error("Error during login for username %s from IP %s: %s", login_data.username, ip_address, str(ex), exc_info=True)
        login_attempt = LoginAttempt(
            user_id=user.id if user else None,
            ip_address=ip_address,
            attempted_username=login_data.username,
            user_agent=user_agent,
            success=False,
            failure_reason=f"Server error: {str(ex)}"
        )
        db.add(login_attempt)
        await db.commit()
        raise 


@router.post("/logout/")
async def logout(
    request: Request,
    response: Response,
    db: DB,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """
    Logout user by clearing cookies and revoking current session token only
    """
    try:
        # Get the current token
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        else:
            token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)
        
        if token:
            # Decode to get JTI
            try:
                payload = security.decode_token(token)
                jti = payload.get("jti")
                ip_address = get_client_ip(request)
                
                if jti:
                    # Revoke only tokens from current IP/device
                    result = await db.execute(
                        select(TokenTracking).where(
                            TokenTracking.user_id == current_user.id,
                            TokenTracking.ip_address == ip_address,
                            TokenTracking.is_active
                        )
                    )
                    tokens = result.scalars().all()
                    
                    for token_tracking in tokens:
                        token_tracking.is_active = False
                        token_tracking.revoked_at = datetime.now(timezone.utc)
                        token_tracking.revoke_reason = "User logout from this device"
                    
                    await db.commit()
                    await db.commit()
                    # Invalidate cached token list so revoked tokens are not served from cache
                    await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
            except Exception:
                pass
        
        clear_auth_cookies(response)
        # await analytics.capture(str(current_user.id), AuthEvents.LOGGED_OUT)
        return {"message": "Successfully logged out from this device"}
    except Exception:
        await db.rollback()
        raise
