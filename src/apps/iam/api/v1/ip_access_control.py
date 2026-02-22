from typing import Sequence
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.models.ip_access_control import IPAccessControl
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.ip_access_control import IPAccessControlResponse, IPAccessControlUpdate

router = APIRouter()


@router.get("/", response_model=list[IPAccessControlResponse])
async def list_ip_access_controls(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Sequence[IPAccessControl]:
    """
    Get all IP access control entries for the current user
    """
    try:
        result = await db.execute(
            select(IPAccessControl).where(
                IPAccessControl.user_id == current_user.id 
            ).order_by(desc(IPAccessControl.last_seen))
        )
        return result.scalars().all()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred fetching IP access controls"
        )


@router.get("/{ip_id}", response_model=IPAccessControlResponse)
async def get_ip_access_control(
    ip_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> IPAccessControl:
    """
    Get specific IP access control entry
    """
    try:
        result = await db.execute(
            select(IPAccessControl).where(
                IPAccessControl.id == ip_id, 
                IPAccessControl.user_id == current_user.id 
            )
        )
        ip_control = result.scalars().first()
        
        if not ip_control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP access control entry not found"
            )
        
        return ip_control
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred fetching IP access control"
        )


@router.patch("/{ip_id}", response_model=IPAccessControlResponse)
async def update_ip_access_control(
    ip_id: int,
    update_data: IPAccessControlUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> IPAccessControl:
    """
    Update IP access control status (whitelist or blacklist)
    """
    try:
        result = await db.execute(
            select(IPAccessControl).where(
                IPAccessControl.id == ip_id, 
                IPAccessControl.user_id == current_user.id 
            )
        )
        ip_control = result.scalars().first()
        
        if not ip_control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP access control entry not found"
            )
        
        ip_control.status = update_data.status
        ip_control.reason = update_data.reason
        
        # If blacklisting, revoke all tokens from this IP
        if update_data.status == "blacklisted":
            token_result = await db.execute(
                select(TokenTracking).where(
                    TokenTracking.user_id == current_user.id, 
                    TokenTracking.ip_address == ip_control.ip_address, 
                    TokenTracking.is_active 
                )
            )
            tokens = token_result.scalars().all()
            
            for token in tokens:
                token.is_active = False
                token.revoked_at = datetime.now(timezone.utc)
                token.revoke_reason = f"IP {ip_control.ip_address} blacklisted"
        
        await db.commit()
        await db.refresh(ip_control)
        
        return ip_control
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred updating IP access control"
        )


@router.delete("/{ip_id}")
async def delete_ip_access_control(
    ip_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Delete IP access control entry
    """
    try:
        result = await db.execute(
            select(IPAccessControl).where(
                IPAccessControl.id == ip_id, 
                IPAccessControl.user_id == current_user.id 
            )
        )
        ip_control = result.scalars().first()
        
        if not ip_control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP access control entry not found"
            )
        
        await db.delete(ip_control)
        await db.commit()
        
        return {"message": "IP access control entry deleted successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred deleting IP access control"
        )
