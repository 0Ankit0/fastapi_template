from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.apps.iam.models.user import User
from src.apps.iam.schemas.token_tracking import TokenTrackingResponse
from src.apps.iam.services.tokens import token_service
from src.core.dependencies import DB, get_current_user
from src.core.pagination import CursorSortDirection
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination
from src.core.types import HashId

router = APIRouter(prefix="/token-management", tags=["Token Management"])
limiter = Limiter(key_func=get_remote_address)

TOKEN_MANAGEMENT_RATE_LIMIT = limiter.limit("10/minute")


@router.get(
    "/",
    response_model=CursorPage[TokenTrackingResponse],
    summary="List Active Sessions",
    description="Cursor-paginated listing of active user token sessions with stable datetime ordering.",
)
@TOKEN_MANAGEMENT_RATE_LIMIT
async def list_active_tokens(
    request: Request,
    db: DB,
    pagination: CursorPagination = Depends(),
    sort_direction: CursorSortDirection = Query(
        default=CursorSortDirection.DESC,
        description="Sort active sessions by latest or oldest",
    ),
    current_user: User = Depends(get_current_user),
):
    return await token_service.list_active_tokens(
        db,
        current_user=current_user,
        pagination=pagination,
        sort_direction=sort_direction,
    )


@router.post(
    "/revoke/{token_id}",
    response_model=ApiSuccessResponse[None],
    summary="Revoke Session Token",
    description="Revokes a single active token session for the authenticated user.",
)
@TOKEN_MANAGEMENT_RATE_LIMIT
async def revoke_token(
    token_id: HashId,
    request: Request,
    db: DB,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[None]:
    return await token_service.revoke_token(db, token_id=token_id, current_user=current_user)


@router.post(
    "/revoke-all",
    response_model=ApiSuccessResponse[dict[str, int]],
    summary="Revoke All Sessions",
    description="Revokes all currently active token sessions for the authenticated user.",
)
@TOKEN_MANAGEMENT_RATE_LIMIT
async def revoke_all_tokens(
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[dict[str, int]]:
    return await token_service.revoke_all_tokens(db, current_user=current_user)


@router.get(
    "/insights",
    response_model=ApiSuccessResponse[dict[str, int]],
    summary="Get Session Insights",
    description="Returns token session aggregates including active, revoked, and expiring-in-24h counts.",
)
@TOKEN_MANAGEMENT_RATE_LIMIT
async def token_insights(
    request: Request,
    db: DB,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[dict[str, int]]:
    return await token_service.token_insights(db, current_user=current_user)
