from datetime import timedelta, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.apps.core.config import settings
from src.apps.core import security
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User, UserProfile
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import UserCreate

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/signup/")
@limiter.limit("3/hour")
async def signup(
    request: Request,
    response: Response,
    set_cookie: bool,
    login_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Token | dict[str, str]:
    """
    Create a new user account
    """
    try:
        result = await db.execute(
            select(User).where(User.username == login_data.username)
        )
        user = result.scalars().first()

        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        hashed_password = security.get_password_hash(login_data.password)
        new_user = User(
           username=login_data.username,
           email=login_data.email,
            hashed_password=hashed_password,
            profile=None
        )
        user_profile = UserProfile(
            first_name=login_data.first_name or "",
            last_name=login_data.last_name or "",
            phone=login_data.phone or "",
            user=new_user
        )
        
        db.add(new_user)
        db.add(user_profile)
        await db.commit()

        from src.apps.iam.services.email import EmailService
        await EmailService.send_welcome_email(new_user)
        
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            new_user.id, expires_delta=access_token_expires
        )
        
        refresh_token = security.create_refresh_token(new_user.id)
        
        # Decode tokens to get JTI
        access_payload = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        refresh_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        
        # Track access token
        access_token_tracking = TokenTracking(
            user_id=new_user.id,
            token_jti=access_payload["jti"],
            token_type="access",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.fromtimestamp(access_payload["exp"], tz=timezone.utc)
        )
        db.add(access_token_tracking)
        
        # Track refresh token
        refresh_token_tracking = TokenTracking(
            user_id=new_user.id,
            token_jti=refresh_payload["jti"],
            token_type="refresh",
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc)
        )
        db.add(refresh_token_tracking)
        await db.commit()

        if set_cookie:
            response.set_cookie(
                key=settings.ACCESS_TOKEN_COOKIE,
                value=access_token,
                httponly=True,
                secure=settings.SECURE_COOKIES,
                samesite="lax",
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            return {"message": "Account created successfully"}
        
        return Token(
            access=access_token,
            refresh=refresh_token,
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during signup"
        )


@router.post("/verify-email/")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Verify user email with token sent via email
    """
    try:
        payload = security.verify_token(token, token_type="email_verification")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    try:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_confirmed = True
        await db.commit()
        
        return {"message": "Email verified successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email verification"
        )


@router.post("/resend-verification/")
async def resend_verification_email(
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Resend email verification link
    """
    try:
        if current_user.is_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        verification_token = security.create_email_verification_token(current_user.id)
        
        from src.apps.iam.services.email import EmailService
        await EmailService.send_verification_email(current_user, verification_token)
        
        return {"message": "Verification email sent"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred sending verification email"
        )
