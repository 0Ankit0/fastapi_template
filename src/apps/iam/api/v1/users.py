"""
User management endpoints with caching and pagination
"""
from fastapi import APIRouter, Depends, Query, UploadFile, File, Request
from src.core.exceptions import ValidationError
from src.core.types import HashId
from src.core.dependencies import DB, CurrentOrg, CurrentUser, CurrentActiveSuperuser
from src.apps.iam.schemas.user import UserResponse, UserUpdate
from src.core.schemas import CursorPage, CursorPagination, ApiSuccessResponse
from src.core.logging import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.pagination import CursorSortDirection
from src.apps.iam.services.users import user_service
from src.core.storage import save_media_bytes, delete_media

limiter = Limiter(key_func=get_remote_address)
logger = get_logger(__name__)

USER_RATE_LIMIT = limiter.limit("10/minute")
router = APIRouter(prefix="/users",tags=["Users"])

@router.get(
    "/{org}/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the authenticated user's profile data enriched with organization roles.",
)
@USER_RATE_LIMIT
async def get_current_user_profile(
    request: Request,
    current_org: CurrentOrg,
    current_user: CurrentUser,
):
    """
    Get current user's profile
    """
    return await user_service.get_current_user_profile(
        current_user=current_user,
        org_slug=current_org.slug if current_org else None,
    )

@router.get(
    "/{org}",
    response_model=CursorPage[UserResponse],
    summary="List Organization Users",
    description="Cursor-paginated organization user listing with search, active/inactive filtering, and sort direction.",
)
@USER_RATE_LIMIT
async def list_users(
    db: DB,
    request: Request,
    current_user: CurrentActiveSuperuser,
    current_org: CurrentOrg,
    pagination: CursorPagination = Depends(),
    search: str | None = Query(
        default=None,
        description="Search by email or name",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status",
    ),
    sort_direction: CursorSortDirection = Query(
        default=CursorSortDirection.ASC,
        description="Sort users by id asc/desc",
    ),
):
    """
    List all users with cursor pagination and optional filters.
    """
    if not current_org:
        raise ValidationError("Current organization not found")

    return await user_service.list_users(
        db,
        org_slug=str(current_org.slug),
        pagination=pagination,
        search=search,
        is_active=is_active,
        sort_direction=sort_direction,
    )


@router.get(
    "/{org}/insights",
    response_model=ApiSuccessResponse[dict[str, int]],
    summary="Get User Insights",
    description="Returns user membership KPIs for the selected organization, including active/inactive and superuser counts.",
)
@USER_RATE_LIMIT
async def user_insights(
    db: DB,
    request: Request,
    current_user: CurrentActiveSuperuser,
    current_org: CurrentOrg,
):
    if not current_org:
        raise ValidationError("Current organization not found")
    return await user_service.user_insights(db, org_slug=str(current_org.slug))

@router.post(
    "/{org}/me/avatar",
    response_model=UserResponse,
    summary="Upload user avatar",
    description="Uploads or replaces the authenticated user's organization-scoped profile avatar.",
)
@USER_RATE_LIMIT
async def upload_avatar(
    db: DB,
    request: Request,
    current_user: CurrentUser,
    current_org: CurrentOrg,
    file: UploadFile = File(...),
) -> UserResponse:
    """Upload or replace the current user's avatar image."""
    return await user_service.upload_avatar(
        db,
        current_user=current_user,
        org_slug=current_org.slug if current_org else None,
        file=file
    )

@router.get("/{org}/{user_id}", response_model=UserResponse)
@USER_RATE_LIMIT
async def get_user(
    user_id: HashId,
    db: DB,
    request: Request,
    current_user: CurrentActiveSuperuser,
    current_org: CurrentOrg
)-> UserResponse:
    """
    Get user by ID (admin only)
    """
    return await user_service.get_user(
        db,
        user_id=user_id,
        org_slug=current_org.slug if current_org else None,
    )

@router.patch("/me", response_model=UserResponse)
@USER_RATE_LIMIT
async def update_current_user(
    user_update: UserUpdate,
    db: DB,
    request: Request,
    current_user: CurrentUser,
):
    """
    Update current user's profile
    """
    return await user_service.update_current_user(
        db,
        current_user=current_user,
        user_update=user_update,
    )

@router.patch("/{org}/{user_id}", response_model=UserResponse)
@USER_RATE_LIMIT
async def update_user(
    user_id: HashId,
    user_update: UserUpdate,
    db: DB,
    request: Request,
    current_user: CurrentActiveSuperuser,
    current_org: CurrentOrg
):
    """
    Update user by ID (admin only)
    """
    return await user_service.update_user(
        db,
        user_id=user_id,
        user_update=user_update,
    )

@router.delete("/{org}/{user_id}")
@USER_RATE_LIMIT
async def delete_user(
    user_id: HashId,
    db: DB,
    request: Request,
    current_user: CurrentActiveSuperuser,
):
    """
    Delete user by ID (admin only)
    """
    return await user_service.delete_user(
        db,
        user_id=user_id,
        current_user_id=current_user.id,
    )