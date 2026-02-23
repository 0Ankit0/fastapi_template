"""
User management endpoints with caching and pagination
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, or_
from typing import Optional
from src.apps.iam.api.deps import get_current_user, get_current_active_superuser, get_db
from src.apps.iam.models.user import User
from src.apps.iam.schemas.user import UserResponse, UserUpdate
from src.apps.core.schemas import PaginatedResponse
from src.apps.core.cache import RedisCache

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of items to return"),
    search: Optional[str] = Query(default=None, description="Search by email or name"),
    is_active: Optional[bool] = Query(default=None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users with pagination and optional filters (admin only)
    """
    # Create cache key including filters
    cache_key = f"users:list:{skip}:{limit}:{search}:{is_active}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    # Build query
    query = select(User)
    count_query = select(func.count(User.id))
    
    # Apply filters
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)
    
    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # Get paginated data
    query = query.offset(skip).limit(limit).order_by(User.id)
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Create response
    response = PaginatedResponse[UserResponse].create(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Cache for 2 minutes (users data changes frequently)
    await RedisCache.set(cache_key, response.model_dump(), ttl=120)
    
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile
    """
    cache_key = f"user:profile:{current_user.id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return UserResponse(**cached)
    
    # Cache for 5 minutes
    await RedisCache.set(cache_key, current_user.model_dump(), ttl=300)
    
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user by ID (admin only)
    """
    cache_key = f"user:profile:{user_id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return UserResponse(**cached)
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Cache for 5 minutes
    await RedisCache.set(cache_key, user.model_dump(), ttl=300)
    
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile
    """
    # Update user fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
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
        current_user.is_verified = False  # Re-verify email
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    # Invalidate caches
    await RedisCache.delete(f"user:profile:{current_user.id}")
    await RedisCache.clear_pattern("users:list:*")
    
    return current_user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user by ID (admin only)
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
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
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Invalidate caches
    await RedisCache.delete(f"user:profile:{user_id}")
    await RedisCache.clear_pattern("users:list:*")
    await RedisCache.clear_pattern(f"user:{user_id}:*")
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db)
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
    await RedisCache.delete(f"user:profile:{user_id}")
    await RedisCache.clear_pattern("users:list:*")
    await RedisCache.clear_pattern(f"user:{user_id}:*")
    await RedisCache.delete(f"casbin:roles:{user_id}")
    await RedisCache.delete(f"casbin:permissions:{user_id}")
    
    return {"message": "User deleted successfully"}
