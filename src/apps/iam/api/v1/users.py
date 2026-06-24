"""
User management endpoints with caching and pagination
"""
from typing import Annotated
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Request
from sqlalchemy.orm import selectinload
from src.core.types import HashId
from src.apps.organizations.models.organization import Organization
from src.core.eums import UserStatus
from src.core.utils import decode_cursor, encode_cursor
from src.db.query import col, func, or_, select
from src.core.dependencies import DB, get_current_user, get_current_active_superuser, get_current_org
from src.apps.iam.models.user import User
from src.apps.iam.schemas.user import UserResponse, UserUpdate
from src.core.schemas import CursorPage, CursorPagination
from src.core.cache import RedisCache
from src.core.config import settings
from src.apps.iam.models import UserProfile
from src.apps.iam.services.policy_service import PolicyService
from src.core.storage import save_media_bytes, delete_media
from src.core.logging import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
logger = get_logger(__name__)

USER_RATE_LIMIT = limiter.limit("10/minute")
router = APIRouter(prefix="/users",tags=["Users"])

def _serialize_user_response(user: User) -> dict[str, object]:
    response = UserResponse.model_validate(user)
    return {
        "id": response.id,
        "username": response.username,
        "email": str(response.email),
        "is_active": response.is_active,
        "is_superuser": response.is_superuser,
        "is_confirmed": response.is_confirmed,
        "otp_enabled": response.otp_enabled,
        "otp_verified": response.otp_verified,
        "first_name": response.first_name,
        "last_name": response.last_name,
        "phone": response.phone,
        "image_url": response.image_url,
        "bio": response.bio,
        "roles": response.roles,
    }


async def _invalidate_user_cache(user_id: int) -> None:
    await RedisCache.delete(f"user:profile:{user_id}")
    await RedisCache.clear_pattern(f"user:{user_id}:*")
    # await RedisCache.clear_pattern(f"casbin:roles:{user_id}:*")
    # await RedisCache.clear_pattern(f"casbin:permissions:{user_id}:*")
    # await RedisCache.clear_pattern(f"permission:check:{user_id}:*")


@router.get("/{org}", response_model=CursorPage[UserResponse])
@USER_RATE_LIMIT
async def list_users(
    db: DB,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_superuser)],
    current_org: Annotated[Organization, Depends(get_current_org)],
    pagination: CursorPagination = Depends(),
    search: str | None = Query(
        default=None,
        description="Search by email or name",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status",
    ),
):
    """
    List all users with cursor pagination and optional filters.
    """

    cache_key = (
        f"users:list:"
        f"{pagination.cursor}:"
        f"{pagination.limit}:"
        f"{search}:"
        f"{is_active}"
    )

    cached = await RedisCache.get(cache_key)
    if cached:
        return cached

    query = (
        select(User)
        .options(
            selectinload(User.profile),
        )
    )
    if not current_org:
        raise ValidationError("Current organization not found")
    
    role_map = PolicyService.get_org_roles(current_org.slug)
        
    if search:
        search_filter = or_(
            col(User.email).ilike(f"%{search}%"),
            col(User.username).ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    if is_active is not None:
        query = query.where(
            User.status == UserStatus.ACTIVE
        )

    if pagination.cursor:
        _, cursor_id = decode_cursor(
            pagination.cursor
        )

        query = query.where(
            User.id > int(cursor_id)
        )

    query = (
        query.order_by(col(User.id))
        .limit(pagination.limit + 1)
    )

    result = await db.execute(query)
    users = result.scalars().all()

    has_next_page = (
        len(users) > pagination.limit
    )

    if has_next_page:
        users = users[: pagination.limit]

    items = [
        UserResponse(
            **UserResponse.model_validate(user).model_dump(exclude={"roles"}),
            roles=role_map.get(user.id, [])
        ) 
        for user in users
    ]
    

    next_cursor = None

    if has_next_page and users:
        next_cursor = encode_cursor(
            users[-1].id
        )

    response = CursorPage[UserResponse](
        items=items,
        next_cursor=next_cursor,
    )

    await RedisCache.set(
        cache_key,
        response.model_dump(mode="json"),
        ttl=120,
    )

    return response

@router.get("/me", response_model=UserResponse)
@USER_RATE_LIMIT
async def get_current_user_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's profile
    """
    cache_key = f"user:profile:{current_user.id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return UserResponse.model_validate(cached)
    
    cache_data = _serialize_user_response(current_user)
    # Cache for 5 minutes
    await RedisCache.set(cache_key, cache_data, ttl=300)
    
    return current_user

@router.post("/me/avatar", response_model=UserResponse)
@USER_RATE_LIMIT
async def upload_avatar(
    db: DB,
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload or replace the current user's avatar image."""
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    MAX_SIZE = settings.MAX_AVATAR_SIZE_MB * 1024 * 1024

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: jpeg, png, gif, webp",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_AVATAR_SIZE_MB} MB",
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"
    filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    relative_path = f"avatars/{filename}"

    if current_user.profile and current_user.profile.avatar_url:
        delete_media(current_user.profile.avatar_url)

    image_url = save_media_bytes(
        relative_path,
        contents,
        content_type=file.content_type,
    )

    if current_user.profile:
        current_user.profile.avatar_url = image_url
        db.add(current_user.profile)
    else:
        from src.apps.iam.models import UserProfile
        profile = UserProfile(user_id=current_user.id, avatar_url=image_url)
        db.add(profile)
        current_user.profile = profile

    await db.commit()
    await db.refresh(current_user)
    if current_user.profile:
        await db.refresh(current_user.profile)

    await _invalidate_user_cache(current_user.id)

    return current_user

@router.get("/{user_id}", response_model=UserResponse)
@USER_RATE_LIMIT
async def get_user(
    user_id: HashId,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_active_superuser)
):
    """
    Get user by ID (admin only)
    """
    cache_key = f"user:profile:{user_id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return UserResponse.model_validate(cached)
    
    result = await db.execute(
        select(User).options(
            selectinload(User.profile),
        ).where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    cache_data = _serialize_user_response(user)
    # Cache for 5 minutes
    await RedisCache.set(cache_key, cache_data, ttl=300)
    
    return user

@router.patch("/me", response_model=UserResponse)
@USER_RATE_LIMIT
async def update_current_user(
    user_update: UserUpdate,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Update current user's profile
    """
    # Update user fields
    if user_update.email is not None:
        # Check if email is already taken
        result = await db.execute(
            select(User).where(
                User.email == user_update.email,
                User.id != current_user.id
            )
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email
        current_user.is_confirmed = False  # Re-verify email

    # Update profile fields
    if current_user.profile:
        if user_update.first_name is not None:
            current_user.profile.first_name = user_update.first_name
        if user_update.last_name is not None:
            current_user.profile.last_name = user_update.last_name
        if user_update.phone is not None:
            current_user.profile.phone = user_update.phone
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    if current_user.profile:
        await db.refresh(current_user.profile)
    
    # Invalidate caches
    await _invalidate_user_cache(current_user.id)
    await RedisCache.clear_pattern("users:list:*")

    updated_fields = user_update.model_dump(exclude_unset=True)

    return current_user

@router.patch("/{user_id}", response_model=UserResponse)
@USER_RATE_LIMIT
async def update_user(
    user_id: HashId,
    user_update: UserUpdate,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Update user by ID (admin only)
    """
    result = await db.execute(
        select(User).options(
            selectinload(User.profile),
        ).where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.email is not None:
        # Check if email is already taken
        result = await db.execute(
            select(User).where(
                User.email == user_update.email,
                User.id != user_id
            )
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_update.email
    
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalars().first()

    # Update profile fields
    if profile:
        if user_update.first_name is not None:
            profile.first_name = user_update.first_name
        if user_update.last_name is not None:
            profile.last_name = user_update.last_name
        if user_update.phone is not None:
            profile.phone = user_update.phone
        db.add(profile)
    elif any(
        value is not None
        for value in [user_update.first_name, user_update.last_name, user_update.phone]
    ):
        profile = UserProfile(
            user_id=user.id,
            first_name=user_update.first_name,
            last_name=user_update.last_name,
            phone=user_update.phone,
        )
        db.add(profile)

    db.add(user)
    await db.commit()
    if profile:
        await db.refresh(profile)
        user.profile = profile
    result = await db.execute(
        select(User).options(
            selectinload(User.profile),
        ).where(User.id == user_id)
    )
    user = result.scalars().first()
    assert user is not None
    
    # Invalidate caches
    await _invalidate_user_cache(user.id)
    await RedisCache.clear_pattern("users:list:*")
    

    return user

@router.delete("/{user_id}")
@USER_RATE_LIMIT
async def delete_user(
    user_id: HashId,
    db: DB,
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Delete user by ID (admin only)
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await db.delete(user)
    await db.commit()
    
    # Invalidate caches
    await _invalidate_user_cache(user.id)
    await RedisCache.clear_pattern("users:list:*")
    
    return {"message": "User deleted successfully"}