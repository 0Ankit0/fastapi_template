from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Body
from app.api import deps
from app.models.user import User, UserProfile
from app.schemas.user import UserRead, UserUpdate
from app.db.session import AsyncSession
from sqlmodel import select
from app.core.security import get_password_hash, verify_password

router = APIRouter()

@router.get("/me/", response_model=UserRead)
async def read_user_me(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    return current_user

@router.delete("/me/", response_model=UserRead)
async def delete_user_me(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    current_user.is_active = False # Soft delete
    db.add(current_user)
    await db.commit()
    return current_user

@router.patch("/me/", response_model=UserRead)
async def update_user_me(
    user_in: UserUpdate,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    if user_in.email and user_in.email != current_user.email:
        result = await db.execute(select(User).where(User.email == user_in.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already taken")
            
    user_data = user_in.dict(exclude_unset=True)
    for field, value in user_data.items():
        setattr(current_user, field, value)
        
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

# --- Profile Endpoints ---

@router.get("/profile/", response_model=UserProfile)
async def read_user_profile(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    # Check if profile exists
    if not current_user.profile:
        # Should have been created/loaded?
        # If relation is lazy, it might not be there.
        # But SQLModel `Relationship` with async?
        # Need to fetch.
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
        profile = result.scalars().first()
        if not profile:
            # Create one if missing?
            profile = UserProfile(user_id=current_user.id)
            db.add(profile)
            await db.commit()
            await db.refresh(profile)
        return profile
    return current_user.profile

@router.patch("/profile/", response_model=UserProfile)
async def update_user_profile(
    # Using generic dict or schema
    backend_profile_in: dict = Body(...), # Todo use UserProfileUpdate schema
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
    
    # Simple dict update
    # In real app use Schema
    for k, v in backend_profile_in.items():
        if hasattr(profile, k):
            setattr(profile, k, v)
            
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

# --- Password Operations ---

@router.post("/change-password/")
async def change_password(
    password_data: dict = Body(...),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    old_password = password_data.get("old_password")
    new_password = password_data.get("new_password")
    
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
        
    current_user.hashed_password = get_password_hash(new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "Password updated successfully"}

@router.post("/password-reset/")
async def request_password_reset(
    email_data: dict = Body(...),
) -> Any:
    # Stub
    return {"message": "If email exists, reset link sent"}

@router.post("/password-reset/confirm/")
async def confirm_password_reset(
    data: dict = Body(...),
) -> Any:
    # Stub
    return {"message": "Password reset successfully"}
