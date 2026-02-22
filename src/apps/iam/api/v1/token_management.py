from typing import Sequence
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token_tracking import TokenTrackingResponse

router = APIRouter()


@router.get("/", response_model=list[TokenTrackingResponse])
async def list_active_tokens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Sequence[TokenTracking]:
    """
    Get all active tokens for the current user
    """
    try:
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.user_id == current_user.id,
                TokenTracking.is_active
            ).order_by(desc(TokenTracking.created_at))
        )
        return result.scalars().all()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred fetching active tokens"
        )


@router.post("/revoke/{token_id}")
async def revoke_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Revoke a specific token
    """
    try:
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.id == token_id,
                TokenTracking.user_id == current_user.id
            )
        )
        token_tracking = result.scalars().first()
        
        if not token_tracking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        
        if not token_tracking.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token is already revoked"
            )
        
        token_tracking.is_active = False
        token_tracking.revoked_at = datetime.now(timezone.utc)
        token_tracking.revoke_reason = "Revoked by user"
        await db.commit()
        
        return {"message": "Token revoked successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred revoking token"
        )


@router.post("/revoke-all")
async def revoke_all_tokens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Revoke all active tokens for the current user
    """
    try:
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
            token_tracking.revoke_reason = "All tokens revoked by user"
        
        await db.commit()
        
        return {"message": f"Revoked {len(tokens)} active token(s)"}
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred revoking tokens"
        )
