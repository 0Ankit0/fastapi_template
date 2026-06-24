from datetime import timedelta, datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from apps.iam.schemas.otp import OtpEnableResponse
from core.schemas import ApiSuccessResponse
from src.core.exceptions import AuthorizationError, RateLimitError, ValidationError, NotFoundError
from src.db.query import select
from sqlalchemy.ext.asyncio import AsyncSession
import pyotp
import qrcode
from io import BytesIO
import base64
from src.core.config import settings
from src.core import security
from src.core.security import TokenType
from src.core.cookies import set_auth_cookies
from src.core.dependencies import DB, get_current_user
from src.apps.iam.models.user import User
from src.apps.iam.models.login_attempt import LoginAttempt
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import VerifyOTPRequest, DisableOTPRequest
from src.core.cache import RedisCache
from src.apps.iam.utils.ip_access import revoke_tokens_for_ip, get_client_ip
from src.core.logging import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
logger = get_logger(__name__)

router = APIRouter()

OTP_RATE_LIMIT = limiter.limit("1/second")

@router.post("/otp/enable/", response_model=ApiSuccessResponse[OtpEnableResponse])
@OTP_RATE_LIMIT
async def enable_otp(
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[OtpEnableResponse]:
    """
    Enable 2FA/OTP for the user account
    """
    try:
        if current_user.otp_enabled:
            raise ValidationError(
                "OTP is already enabled for this account"
            )
        
        # Generate OTP secret
        otp_base32 = pyotp.random_base32()
        otp_auth_url = pyotp.totp.TOTP(otp_base32).provisioning_uri(
            name=current_user.email,
            issuer_name=settings.APP_INSTANCE_NAME
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(otp_auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to pillow image
        pill_img = img.get_image()

        # Convert to base64
        buffered = BytesIO()
        pill_img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Save OTP settings (but don't enable yet, wait for verification)
        current_user.otp_base32 = otp_base32
        current_user.otp_auth_url = otp_auth_url
        current_user.otp_verified = False
        await db.commit()
        
        return ApiSuccessResponse[OtpEnableResponse](
            message="OTP setup initiated. Please verify OTP code to enable.",
            data=OtpEnableResponse(
                otp_base32=otp_base32,
                auth_uri=otp_auth_url,
                qr_code=f"data:image/png;base64,{qr_code_base64}"
            )
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise 


@router.post("/otp/verify/", response_model=ApiSuccessResponse[None])
@OTP_RATE_LIMIT
async def verify_otp(
    otp_data: VerifyOTPRequest,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[None]:
    """
    Verify and activate OTP for the user
    """
    try:
        if not current_user.otp_base32:
            raise ValidationError(
                "OTP setup not initiated for this account"
            )
        
        totp = pyotp.TOTP(current_user.otp_base32)
        if not totp.verify(otp_data.otp_code):
            raise ValidationError(
                "Invalid OTP code"
            )
               
        
        current_user.otp_enabled = True
        current_user.otp_verified = True
        await db.commit()
        
        # Invalidate user cache
        await RedisCache.delete(f"user:profile:{current_user.id}")

        return ApiSuccessResponse[None](message="OTP verified and enabled successfully")
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise 


@router.post("/otp/disable/", response_model=ApiSuccessResponse[None])
@OTP_RATE_LIMIT
async def disable_otp(
    otp_data: DisableOTPRequest,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[None]:
    """
    Disable 2FA/OTP for the user account
    """
    try:
        if not current_user.otp_enabled:
            raise ValidationError(
                "OTP is not enabled"
            )
        
        
        # Verify password before disabling
        if not security.verify_password(otp_data.password, current_user.hashed_password): # type: ignore
            raise ValidationError(
                "Incorrect password"
            )
        
        current_user.otp_enabled = False
        current_user.otp_verified = False
        current_user.otp_base32 = ""
        current_user.otp_auth_url = ""
        await db.commit()
        
        # Invalidate user cache
        await RedisCache.delete(f"user:profile:{current_user.id}")

        return ApiSuccessResponse[None](message="OTP disabled successfully")
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise 


@router.post("/otp/validate/", response_model=ApiSuccessResponse[Token] | ApiSuccessResponse[None])
@OTP_RATE_LIMIT
async def validate_otp_login(
    otp_data: VerifyOTPRequest,
    request: Request,
    response: Response,
    db: DB,
    set_cookie: bool = False,
) -> ApiSuccessResponse[Token] | ApiSuccessResponse[None]:
    """
    Validate OTP during login process (called after username/password validation).
    Pass set_cookie=true to receive the access token via HttpOnly cookie instead of JSON.
    """
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    user = None

    try:
        # Get user from temporary session or token
        # temp_token = request.headers.get("X-Temp-Auth-Token")
        temp_token = otp_data.temp_token
        if not temp_token:
            raise AuthorizationError("Temporary token required for OTP validation")
        
        try:
            payload = security.verify_token(temp_token, token_type=TokenType.TEMP_AUTH)
            user_id = payload.get("sub")
            if not user_id:
                raise AuthorizationError("Invalid temporary token")
        except Exception:
            raise AuthorizationError(
                message="Invalid temporary token"
            )
        
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()

        if not user:
            raise AuthorizationError("Invalid temporary token")

        if settings.MAX_LOGIN_ATTEMPTS > 0 and settings.ACCOUNT_LOCKOUT_DURATION_MINUTES > 0:
            window_start = datetime.now() - timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
            result = await db.execute(
                select(LoginAttempt)
                .where(
                    LoginAttempt.user_id == user.id,
                    LoginAttempt.success == False,
                    LoginAttempt.timestamp >= window_start,
                )
                .order_by(LoginAttempt.timestamp.desc())
            )
            failures = result.scalars().all()
            if len(failures) >= settings.MAX_LOGIN_ATTEMPTS:
                last_attempt = failures[0]
                lockout_expires = last_attempt.timestamp + timedelta(minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES)
                remaining_seconds = int((lockout_expires - datetime.now()).total_seconds())
                if remaining_seconds > 0:
                    remaining_minutes = (remaining_seconds + 59) // 60
                    raise RateLimitError(
                        f"Account locked due to too many failed OTP attempts. Try again in {remaining_minutes} minute(s)."
                    )
        
        if not user:
            raise NotFoundError("User not found for OTP validation")
        
        if not user.otp_enabled:
            raise ValidationError("OTP not enabled for this account")
        
        totp = pyotp.TOTP(user.otp_base32)
        if not totp.verify(otp_data.otp_code):
            login_attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=user.username,
                user_agent=user_agent,
                success=False,
                failure_reason="Invalid OTP code"
            )
            db.add(login_attempt)
            await db.commit()

            await db.commit()
            raise ValidationError("Invalid OTP code")
        
        # Successful OTP validation - log successful login
        login_attempt = LoginAttempt(
            user_id=user.id,
            ip_address=ip_address,
            attempted_username=user.username,
            user_agent=user_agent,
            success=True,
            failure_reason=""
        )
        db.add(login_attempt)
        
        # Generate actual access tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        refresh_token = security.create_refresh_token(user.id)
        
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
        
        await db.commit()

        if set_cookie:
            set_auth_cookies(
                response,
                access_token=access_token,
                refresh_token=refresh_token,
            )
            return ApiSuccessResponse[None](message="OTP validated successfully")
        
        token_data = Token(
            access=access_token,
            refresh=refresh_token,
            token_type=TokenType.BEARER.value
        )
        return ApiSuccessResponse[Token](message="OTP validated successfully", data=token_data)
    except HTTPException:
        await db.rollback()
        raise
    except Exception as ex:
        await db.rollback()
        if user:
            login_attempt = LoginAttempt(
                user_id=user.id,
                ip_address=ip_address,
                attempted_username=user.username,
                user_agent=user_agent,
                success=False,
                failure_reason=f"Server error during OTP validation: {str(ex)}"
            )
            db.add(login_attempt)
            await db.commit()
            logger.warning(f"Failed OTP validation for user_id={user.id} from IP={ip_address}: {str(ex)}")
        raise 
               