from typing import Sequence
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.iam.models.ip_access_control import IPAccessControl, IpAccessStatus
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.ip_access_control import IPAccessControlResponse, IPAccessControlUpdate
from src.apps.core.schemas import PaginatedResponse
from src.apps.core.cache import RedisCache

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[IPAccessControlResponse])
async def list_ip_access_controls(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of items to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all IP access control entries for the current user with pagination
    """
    try:
        cache_key = f"ip_access:{current_user.id}:{skip}:{limit}"
        
        # Try cache
        cached = await RedisCache.get(cache_key)
        if cached:
            return cached
        
        # Get total count
        count_result = await db.execute(
            select(func.count(IPAccessControl.id)).where( # type: ignore
                IPAccessControl.user_id == current_user.id
            )
        )
        total = count_result.scalar_one()
        
        # Get paginated data
        result = await db.execute(
            select(IPAccessControl).where(
                IPAccessControl.user_id == current_user.id 
            ).order_by(desc(IPAccessControl.last_seen))
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()
        items_response = [IPAccessControlResponse.model_validate(item) for item in items]

        # Create response
        response = PaginatedResponse[IPAccessControlResponse].create(
            items=items_response,
            total=total,
            skip=skip,
            limit=limit
        )
        
        # Cache for 5 minutes
        await RedisCache.set(cache_key, response.model_dump(), ttl=300)
        
        return response
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
        cache_key = f"ip_access:{current_user.id}:{ip_id}"
        
        # Try cache
        cached = await RedisCache.get(cache_key)
        if cached:
            return IPAccessControl(**cached)
        
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
        
        # Cache for 10 minutes
        await RedisCache.set(cache_key, ip_control.model_dump(), ttl=600)
        
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
        
        # Invalidate caches
        await RedisCache.delete(f"ip_access:{current_user.id}:{ip_id}")
        await RedisCache.clear_pattern(f"ip_access:{current_user.id}:*")
        
        # If blacklisting, revoke all tokens from this IP
        if update_data.status == IpAccessStatus.BLACKLISTED:
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


# @router.delete("/{ip_id}")
# async def delete_ip_access_control(
#     ip_id: int,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ) -> dict[str, str]:
#     """
#     Delete IP access control entry
#     """
#     try:
#         result = await db.execute(
#             select(IPAccessControl).where(
#                 IPAccessControl.id == ip_id, 
#                 IPAccessControl.user_id == current_user.id 
#             )
#         )
#         ip_control = result.scalars().first()
        
#         if not ip_control:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="IP access control entry not found"
#             )
        
#         await db.delete(ip_control)
#         await db.commit()
        
#         return {"message": "IP access control entry deleted successfully"}
#     except HTTPException:
#         raise
#     except Exception:
#         await db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="An error occurred deleting IP access control"
#         )


@router.get("/verify")
async def verify_ip_action(
    t: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Verify IP whitelist/blacklist action from email link
    """
    try:
        from src.apps.core import security
        from src.apps.core.security import TokenType
        from src.apps.iam.models.used_token import UsedToken
        
        # Decrypt and verify the secure URL token
        try:
            token_data = security.verify_secure_url_token(t)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification link"
            )
        
        # Extract embedded data
        user_id = token_data.get("user_id")
        ip_address = token_data.get("ip_address")
        action = token_data.get("action")
        jwt_token = token_data.get("token")
        
        if not all([user_id, ip_address, action, jwt_token]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token data"
            )
        assert user_id is not None, "user_id must be present in token data"
        
        # Verify the embedded JWT token
        expected_type = TokenType.IP_WHITELIST if action == "whitelist" else TokenType.IP_BLACKLIST
        payload = security.verify_token(str(jwt_token), token_type=expected_type)
        token_jti = payload.get("jti")
        
        # Verify user_id and ip_address match
        if str(payload.get("sub")) != str(user_id) or payload.get("ip") != ip_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token data mismatch - possible tampering detected"
            )
        
        # Check if token has already been used
        if token_jti:
            used_check = await db.execute(
                select(UsedToken).where(UsedToken.token_jti == token_jti)
            )
            if used_check.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This verification link has already been used"
                )
        
        # Find the IP access control entry
        result = await db.execute(
            select(IPAccessControl).where(
                IPAccessControl.user_id == int(user_id),
                IPAccessControl.ip_address == ip_address
            )
        )
        ip_control = result.scalars().first()
        
        if not ip_control:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="IP access control entry not found"
            )
        
        # Update status based on action
        if action == "whitelist":
            ip_control.status = IpAccessStatus.WHITELISTED
            ip_control.reason = "User verified via email"
            message = "IP address has been whitelisted successfully. You can now access your account from this IP."
        else:
            ip_control.status = IpAccessStatus.BLACKLISTED
            ip_control.reason = "User reported unauthorized access"
            message = "IP address has been blacklisted. If this was a mistake, please contact support."
            
            # Revoke all tokens from this IP
            token_result = await db.execute(
                select(TokenTracking).where(
                    TokenTracking.user_id == int(user_id),
                    TokenTracking.ip_address == ip_address,
                    TokenTracking.is_active
                )
            )
            tokens = token_result.scalars().all()
            
            for token_tracking in tokens:
                token_tracking.is_active = False
                token_tracking.revoked_at = datetime.now(timezone.utc)
                token_tracking.revoke_reason = f"IP {ip_address} blacklisted by user"
        
        # Mark token as used to prevent reuse
        if token_jti:
            used_token = UsedToken(
                token_jti=token_jti,
                user_id=int(user_id),
                token_purpose="ip_action"
            )
            db.add(used_token)
        
        await db.commit()
        
        return {"message": message}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing IP verification"
        )
