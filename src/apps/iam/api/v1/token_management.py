from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from src.core.types import HashId
from src.core.utils import decode_cursor, encode_cursor
from src.db.query import col, desc, func, select
from datetime import datetime, timezone
from src.core.dependencies import DB, get_current_user
from src.apps.iam.models.user import User
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token_tracking import TokenTrackingResponse
from src.core.schemas import CursorPage, CursorPagination
from src.core.cache import RedisCache
from src.db.query import or_, and_
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/token-management", tags=["Token Management"])
limiter = Limiter(key_func=get_remote_address)

TOKEN_MANAGEMENT_RATE_LIMIT = limiter.limit("10/minute")

@router.get(
    "/",
    response_model=CursorPage[TokenTrackingResponse],
)
@TOKEN_MANAGEMENT_RATE_LIMIT
async def list_active_tokens(
    request: Request,
    db: DB,
    pagination: CursorPagination = Depends(),
    current_user: User = Depends(get_current_user),
):
    try:
        query = (
            select(TokenTracking)
            .where(
                TokenTracking.user_id == current_user.id,
                TokenTracking.is_active,
            )
        )

        if pagination.cursor:
            cursor_created_at, cursor_id = decode_cursor(
                pagination.cursor
            )

            query = query.where(
                or_(
                    TokenTracking.created_at < cursor_created_at,
                    and_(
                        TokenTracking.created_at == cursor_created_at,
                        TokenTracking.id < cursor_id,
                    ),
                )
            )

        query = (
            query.order_by(
                desc(TokenTracking.created_at),
                desc(TokenTracking.id),
            )
            .limit(pagination.limit + 1)
        )

        result = await db.execute(query)
        rows = result.scalars().all()

        has_next_page = len(rows) > pagination.limit

        if has_next_page:
            rows = rows[: pagination.limit]

        items = [
            TokenTrackingResponse.model_validate(row)
            for row in rows
        ]

        next_cursor = None

        if has_next_page and rows:
            last = rows[-1]

            next_cursor = encode_cursor(
                last.id,
                last.created_at, 
            )

        return CursorPage[TokenTrackingResponse](
            items=items,
            next_cursor=next_cursor,
        )

    except Exception:
        raise 

@router.post("/revoke/{token_id}")
@TOKEN_MANAGEMENT_RATE_LIMIT
async def revoke_token(
    token_id: HashId,
    request: Request,
    db: DB,
    current_user: User = Depends(get_current_user),
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
        
        # Invalidate cache
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")

        return {"message": "Token revoked successfully"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise 


@router.post("/revoke-all")
@TOKEN_MANAGEMENT_RATE_LIMIT
async def revoke_all_tokens(
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
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
    
        # Invalidate cache
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")

        return {"message": f"Revoked {len(tokens)} active token(s)"}
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred revoking tokens"
        )