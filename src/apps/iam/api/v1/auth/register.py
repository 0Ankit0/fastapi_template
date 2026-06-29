from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from src.apps.iam.models.profile import UserProfile
from src.core.schemas import ApiSuccessResponse
from src.db.query import select
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings
from src.core import security
from src.core.exceptions import AppError, ValidationError
from src.core.security import TokenType
from src.core.cookies import set_auth_cookies
from src.core.dependencies import DB
from src.apps.iam.models import User, UserProfile
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import EmailVerificationRequest, UserCreate
from src.core.cache import RedisCache
from src.core.logging import get_logger
from src.apps.iam.utils.ip_access import revoke_tokens_for_ip, get_client_ip

logger = get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

SIGNUP_RATE_LIMIT = limiter.limit(lambda: settings.RATE_LIMIT_SIGNUP)

@router.post("/signup/", response_model = ApiSuccessResponse[Token])
@SIGNUP_RATE_LIMIT
async def signup(
    request: Request,
    response: Response,
    login_data: UserCreate,
    db: DB,
    set_cookie: bool = False,
) -> ApiSuccessResponse[Token]:
    """
    Create a new user account
    """
    ip_address = get_client_ip(request)
    
    try:
        result = await db.execute(
            select(User).where(User.username == login_data.username)
        )
        user = result.scalars().first()

        if user:
            raise ValidationError(
                message="Username already exists"
            )

        hashed_password = security.get_password_hash(login_data.password)
        new_user : User = User(
           username=login_data.username,
           email=login_data.email,
           password_hash=hashed_password,
        )
        db.add(new_user)
        await db.flush()

        user_profile = UserProfile(
            user_id=new_user.id,
            first_name=login_data.first_name or "",
            last_name=login_data.last_name or "",
            phone=login_data.phone or "",
        )
        db.add(user_profile)
        await db.commit()
        
        # Invalidate users list cache
        await RedisCache.clear_pattern("users:list:*")
        
        from src.apps.iam.services.email import AuthEmailService
        await AuthEmailService.send_welcome_email(new_user)
        
        user_agent = request.headers.get("user-agent", "unknown")
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            new_user.id, expires_delta=access_token_expires
        )
        
        refresh_token = security.create_refresh_token(new_user.id)
        
        access_payload = security.decode_token(access_token)
        refresh_payload = security.decode_token(refresh_token)

        # Revoke any existing active tokens for this user+IP before issuing new ones
        await revoke_tokens_for_ip(db, new_user.id, ip_address)

        # Track access token
        access_token_tracking = TokenTracking(
            user_id=new_user.id,
            token_jti=access_payload["jti"],
            token_type=TokenType.ACCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(access_payload)
        )
        db.add(access_token_tracking)
        
        # Track refresh token
        refresh_token_tracking = TokenTracking(
            user_id=new_user.id,
            token_jti=refresh_payload["jti"],
            token_type=TokenType.REFRESH,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=security.payload_expiration(refresh_payload)
        )
        db.add(refresh_token_tracking)
        await db.commit()

        if set_cookie:
            set_auth_cookies(
                response,
                access_token=access_token,
                refresh_token=refresh_token,
            )
            return ApiSuccessResponse[Token](message="Account created successfully", data=Token(
                access="",
                refresh="",
                token_type=TokenType.BEARER.value
            ))
        
        token_data = Token(
            access=access_token,
            refresh=refresh_token,
            token_type=TokenType.BEARER.value
        )
        return ApiSuccessResponse[Token](message="Account created successfully", data=token_data)
    except (HTTPException, AppError):
        await db.rollback()
        logger.error("Error during signup", exc_info=True)
        raise
    except Exception:
        await db.rollback()
        logger.error("Error during signup", exc_info=True)
        raise 


@router.post("/verify-email/", response_model=ApiSuccessResponse[None])
@SIGNUP_RATE_LIMIT
async def verify_email(
    t: str,
    request: Request,
    db: DB,
) -> ApiSuccessResponse[None]:
    """
    Verify user email with secure token sent via email
    """
    try:
        from src.apps.iam.models import UsedToken
        
        # Decrypt and verify the secure URL token
        try:
            token_data = security.verify_secure_url_token(t)
        except Exception:
            raise ValidationError(
                message="Invalid or expired verification token"
            )
        
        user_id = token_data.get("user_id")
        paseto_token = token_data.get("token")
        purpose = token_data.get("purpose")
        
        if not all([user_id, paseto_token]) or purpose != "email_verification":
            raise ValidationError(
                message="Invalid token data"
            )
        
        
        # Verify the embedded PASETO token
        payload = security.verify_token(str(paseto_token), token_type=TokenType.EMAIL_VERIFICATION)
        token_jti = payload.get("jti")
        
        # Verify user_id matches
        if str(payload.get("sub")) != str(user_id):
            raise ValidationError(
                message="Token data mismatch - possible tampering detected"
            )
        
        # Check if token has already been used
        if token_jti:
            used_check = await db.execute(
                select(UsedToken).where(UsedToken.token_jti == token_jti)
            )
            if used_check.scalars().first():
                raise ValidationError(
                    message="This verification link has already been used"
                )
                
    except (HTTPException, AppError):
        logger.error("Error during email verification", exc_info=True)
        raise
    except Exception:
        logger.error("Error during email verification", exc_info=True)
        raise 
    
    try:
        if not user_id:
            raise ValidationError(
                message="Invalid token data - missing user information"
            )
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        
        if not user:
            raise ValidationError(
                message="User not found for this token"
            )
        
        user.is_confirmed = True
        
        # Mark token as used
        if token_jti:
            used_token = UsedToken(
                token_jti=token_jti,
                user_id=int(user_id),
                token_purpose="email_verification"
            )
            db.add(used_token)
        
        await db.commit()

        # Invalidate user cache
        await RedisCache.delete(f"user:profile:{user_id}")

        return ApiSuccessResponse[None](message="Email verified successfully")
    except (HTTPException, AppError):
        await db.rollback()
        logger.error("Error during email verification", exc_info=True)
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error during email verification.", exc_info=True)
        raise 


@router.post("/resend-verification/", response_model=ApiSuccessResponse[None])
@SIGNUP_RATE_LIMIT
async def resend_verification_email(
    data: EmailVerificationRequest,
    db: DB,
    request: Request
) -> ApiSuccessResponse[None]:
    """
    Resend email verification link
    """
    try:
        user_by_email = await db.execute(select(User).where(User.email == data.email))
        user = user_by_email.scalar_one_or_none()

        if not user:
            return ApiSuccessResponse[None](
                message="If an account with that email exists, a verification email has been sent"
                )

        verification_token = security.create_email_verification_token(user.id)
        
        from src.apps.iam.services.email import AuthEmailService 
        await AuthEmailService.send_verification_email(user, verification_token)
        
        return ApiSuccessResponse[None](
            message="If an account with that email exists, a verification email has been sent"
        )
    except (HTTPException, AppError):
        logger.error("Error during resend verification email", exc_info=True)
        raise
    except Exception:
        logger.error("Error during resend verification email", exc_info=True)
        raise 
