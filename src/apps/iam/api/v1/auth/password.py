from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.apps.core.config import settings
from src.apps.core import security
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.user import (
    ResetPasswordRequest,
    ResetPasswordConfirm,
    ChangePasswordRequest
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


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
    try:
        result = await db.execute(
            select(User).where(User.email == reset_data.email)
        )
        user = result.scalars().first()
        
        if not user:
            return {"message": "If the email exists, a password reset link has been sent"}
        
        reset_token = security.create_password_reset_token(user.id)
        
        from src.apps.iam.services.email import EmailService
        await EmailService.send_password_reset_email(user, reset_token)
        
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
    reset_data: ResetPasswordConfirm,
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Confirm password reset with token and set new password
    """
    try:
        payload = security.verify_token(reset_data.token, token_type="password_reset")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    try:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.hashed_password = security.get_password_hash(reset_data.new_password)
        
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
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Change password for authenticated user
    """
    try:
        if not security.verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        current_user.hashed_password = security.get_password_hash(password_data.new_password)
        
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
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password change"
        )
