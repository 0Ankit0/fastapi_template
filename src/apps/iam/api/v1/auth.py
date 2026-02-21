from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.core.config import settings
from src.apps.core import security
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User, UserProfile
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import (
    LoginRequest, 
    UserCreate, 
    ResetPasswordRequest, 
    ResetPasswordConfirm,
    ChangePasswordRequest,
    VerifyOTPRequest,
    DisableOTPRequest
)
import pyotp
import qrcode
from io import BytesIO
import base64
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/login/")
@limiter.limit("5/minute")
async def login_access_token(
    request: Request,
    response: Response,
    set_cookie: bool,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Token | dict[str, Any]:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    result = await db.execute(
        select(User).where(User.username == login_data.username) # type: ignore
    )
    user = result.scalars().first()

    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Check if OTP is enabled for this user
    if user.otp_enabled and user.otp_verified:
        # Return temporary token, require OTP validation
        temp_token = security.create_temp_auth_token(user.id)
        return {
            "requires_otp": True,
            "temp_token": temp_token,
            "message": "Please provide OTP code"
        }
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    if set_cookie:
        response.set_cookie(
            key=settings.ACCESS_TOKEN_COOKIE,
            value=access_token,
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        return {"message": "Logged in successfully"}
    
    return Token(
        access=access_token,
        refresh=refresh_token,
        token_type="bearer"
    )
    
@router.post("/logout/")
async def logout(
    response: Response
) -> dict[str, str]:
    """
    Logout user by clearing the access token cookie
    """
    response.delete_cookie(key=settings.ACCESS_TOKEN_COOKIE)
    return {"message": "Successfully logged out"}

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
    result = await db.execute(
        select(User).where(User.username == login_data.username) # type: ignore
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
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        new_user.id, expires_delta=access_token_expires
    )
    
    refresh_token = security.create_refresh_token(new_user.id)

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

@router.post("/refresh/")
async def refresh_token(
    response: Response,
    request: Request,
    set_cookie: bool,
    refresh_token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Token | dict[str, str]:
    """
    Refresh access token using a valid refresh token
    """
    if not refresh_token:
        refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE)
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    user_id = security.verify_token(refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    result = await db.execute(select(User).where(User.id == user_id)) # type: ignore
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    new_refresh_token = security.create_refresh_token(user.id)

    if set_cookie:
        response.set_cookie(
            key=settings.ACCESS_TOKEN_COOKIE,
            value=access_token,
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        response.set_cookie(
            key=settings.REFRESH_TOKEN_COOKIE,
            value=new_refresh_token,
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
        return {"message": "Token refreshed successfully"}
    
    return Token(
        access=access_token,
        refresh=new_refresh_token,
        token_type="bearer"
    )

@router.post("/password-reset-request/")
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Request a password reset link via email
    """
    result = await db.execute(
        select(User).where(User.email == reset_data.email) # type: ignore
    )
    user = result.scalars().first()
    
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Create a password reset token (valid for 1 hour)
    reset_token = security.create_password_reset_token(user.id)
    
    from src.apps.iam.services.email import EmailService
    await EmailService.send_password_reset_email(user, reset_token)
    
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/password-reset-confirm/")
async def confirm_password_reset(
    reset_data: ResetPasswordConfirm,
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Confirm password reset with token and set new password
    """
    try:
        payload = security.verify_token(reset_data.token, token_type="password_reset")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id))) # type: ignore
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.hashed_password = security.get_password_hash(reset_data.new_password)
    await db.commit()
    
    return {"message": "Password has been reset successfully"}

@router.post("/change-password/")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Change password for authenticated user
    """
    if not security.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    current_user.hashed_password = security.get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"message": "Password changed successfully"}

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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id))) # type: ignore
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_confirmed = True
    await db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/resend-verification/")
async def resend_verification_email(
    current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    """
    Resend email verification link
    """
    if current_user.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    verification_token = security.create_email_verification_token(current_user.id)
    
    from src.apps.iam.services.email import EmailService
    await EmailService.send_verification_email(current_user, verification_token)
    
    return {"message": "Verification email sent"}

@router.post("/otp/enable/")
async def enable_otp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Enable 2FA/OTP for the user account
    """
    if current_user.otp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP is already enabled"
        )
    
    # Generate OTP secret
    otp_base32 = pyotp.random_base32()
    otp_auth_url = pyotp.totp.TOTP(otp_base32).provisioning_uri(
        name=current_user.email,
        issuer_name=settings.PROJECT_NAME
    )
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(otp_auth_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    # Save OTP settings (but don't enable yet, wait for verification)
    current_user.otp_base32 = otp_base32
    current_user.otp_auth_url = otp_auth_url
    current_user.otp_verified = False
    await db.commit()
    
    return {
        "otp_base32": otp_base32,
        "otp_auth_url": otp_auth_url,
        "qr_code": f"data:image/png;base64,{qr_code_base64}"
    }

@router.post("/otp/verify/")
async def verify_otp(
    otp_data: VerifyOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Verify and activate OTP for the user
    """
    if not current_user.otp_base32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not set up. Please enable OTP first"
        )
    
    totp = pyotp.TOTP(current_user.otp_base32)
    if not totp.verify(otp_data.otp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code"
        )
    
    current_user.otp_enabled = True
    current_user.otp_verified = True
    await db.commit()
    
    return {"message": "OTP verified and enabled successfully"}

@router.post("/otp/disable/")
async def disable_otp(
    otp_data: DisableOTPRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Disable 2FA/OTP for the user account
    """
    if not current_user.otp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP is not enabled"
        )
    
    # Verify password before disabling
    if not security.verify_password(otp_data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    current_user.otp_enabled = False
    current_user.otp_verified = False
    current_user.otp_base32 = ""
    current_user.otp_auth_url = ""
    await db.commit()
    
    return {"message": "OTP disabled successfully"}

@router.post("/otp/validate/")
async def validate_otp_login(
    otp_data: VerifyOTPRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Validate OTP during login process (called after username/password validation)
    """
    # Get user from temporary session or token
    temp_token = request.headers.get("X-Temp-Auth-Token")
    if not temp_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Temporary authentication token required"
        )
    
    try:
        payload = security.verify_token(temp_token, token_type="temp_auth")
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid temporary token"
        )
    
    result = await db.execute(select(User).where(User.id == int(user_id))) # type: ignore
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.otp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not enabled for this account"
        )
    
    totp = pyotp.TOTP(user.otp_base32)
    if not totp.verify(otp_data.otp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code"
        )
    
    # Generate actual access tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    return Token(
        access=access_token,
        refresh=refresh_token,
        token_type="bearer"
    )