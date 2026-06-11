from datetime import datetime, timezone
from typing import cast
from fastapi import APIRouter, Depends, HTTPException, Request, status
from src.core.exceptions import ValidationError
from src.db.query import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.config import settings
from src.core import security
from src.core.security import TokenType
from src.core.dependencies import DB, get_current_user, get_session
from src.apps.iam.models.user import User
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.user import (
    ResetPasswordRequest,
    ResetPasswordConfirm,
    ChangePasswordRequest
)
from src.core.cache import RedisCache

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/password-reset-request/")
@limiter.limit(lambda: settings.RATE_LIMIT_PASSWORD_RESET)
async def request_password_reset(
    request: Request,
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Request a password reset link via email
    """
    try:
        result = await db.execute(
            select(User).where(User.email == reset_data.email)
        )
        user = result.scalars().first()
        
        if not user:
            return {"message": "If the email exists, a password reset link has been sent"}
        
        reset_token = security.create_password_reset_token(user.id)
        
        from src.apps.iam.services.email import AuthEmailService
        await AuthEmailService.send_password_reset_email(user, reset_token)

        return {"message": "If the email exists, a password reset link has been sent"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing password reset request"
        )


@router.post("/password-reset-confirm/")
async def confirm_password_reset(
    body: ResetPasswordConfirm,
    db: DB = Depends(get_session),
) -> dict[str, str]:
    """
    Confirm password reset. Pass the token and new password in the request body.
    """
    try:
        from src.apps.iam.models.used_token import UsedToken
        
        # Decrypt and verify the secure URL token
        try:
            token_data = security.verify_secure_url_token(body.token)
        except Exception:
            raise ValidationError("Invalid or expired reset token")
        
        user_id = token_data.get("user_id")
        paseto_token = token_data.get("token")
        purpose = token_data.get("purpose")
        
        if not all([user_id, paseto_token]) or purpose != "password_reset":
            raise ValidationError("Invalid reset token data")
        
        if not isinstance(paseto_token, str) or not isinstance(user_id, (str, int)):
            raise ValidationError("Invalid token format")

        # Verify the embedded PASETO token
        payload = security.verify_token( paseto_token, token_type=TokenType.PASSWORD_RESET)
        token_jti = payload.get("jti")
        
        # Verify user_id matches
        if str(payload.get("sub")) != str(user_id):
            raise ValidationError("Token data mismatch - possible tampering detected")
        
        # Check if token has already been used
        if token_jti:
            used_check = await db.execute(
                select(UsedToken).where(UsedToken.token_jti == token_jti)
            )
            if used_check.scalars().first():
                raise ValidationError("This password reset link has already been used")
                
    except HTTPException:
        raise
    except Exception:
        raise ValidationError("Invalid or expired reset token")
    
    try:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        
        if not user:
            raise ValidationError("User not found for this reset token")
        
        user.password_hash = security.get_password_hash(body.new_password)
        
        # Mark token as used
        if token_jti:
            used_token = UsedToken(
                token_jti=token_jti,
                user_id=int(user_id),
                token_purpose="password_reset"
            )
            db.add(used_token)
        
        # Revoke all active tokens for this user
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.user_id == user.id,
                TokenTracking.is_active
            )
        )
        tokens = result.scalars().all()
        
        for token_tracking in tokens:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = "Password reset"
        
        await db.commit()
        
        # Invalidate all related caches
        await RedisCache.delete(f"user:profile:{user_id}")
        await RedisCache.clear_pattern(f"tokens:active:{user_id}:*")

        return {"message": "Password has been reset successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset"
        )


@router.post("/change-password/")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: DB = Depends(get_session),
) -> dict[str, str]:
    """
    Change password for authenticated user
    """
    try:
        if not security.verify_password(password_data.current_password, current_user.password_hash):
            raise ValidationError("Current password is incorrect")
        
        current_user.password_hash = security.get_password_hash(password_data.new_password)
        
        # Revoke all active tokens for this user
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.user_id == current_user.id,
                TokenTracking.is_active
            )
        )
        tokens = result.scalars().all()
        
        for token_tracking in tokens:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = "Password changed"
        
        await db.commit()
        
        # Invalidate caches
        await RedisCache.delete(f"user:profile:{current_user.id}")
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")

        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password change"
        )