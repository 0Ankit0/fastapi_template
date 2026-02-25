from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select
from app.core import security
from app.core.config import settings
from app.api import deps
from app.db.session import AsyncSession
from app.models.user import User, UserProfile
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from jose import jwt

router = APIRouter()

@router.post("/token/", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    return {
        "access": access_token,
        "refresh": refresh_token,
        "token_type": "bearer",
    }

# Also handle JSON body login if the frontend sends JSON instead of Form data
# The frontend code sends `credentials` which is typically JSON {email, password}
# But standard OAuth2 form is form-data. 
# Looking at `api-client.ts`, it sends content-type generic, but `use-auth.ts` calls `apiClient.post` with `credentials`.
# Likely JSON. So we need a JSON endpoint too or instead.
# `OAuth2PasswordRequestForm` expects form-data.

from pydantic import BaseModel
class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/token/", response_model=Token)
async def login_json(
    response: Response,
    login_data: LoginRequest,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    
    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
        secure=False 
    )
    
    return {
        "access": access_token,
        "refresh": refresh_token,
        "token_type": "bearer",
    }

@router.post("/signup/", response_model=Token)
async def signup(
    response: Response,
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Create new user without the need to be logged in
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system",
        )
    
    user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create UserProfile
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.commit()
    
    # Associate Invitations
    from app.services.tenant_service import TenantService
    await TenantService.associate_invitations(db, user.email, user.id)

    # Ensure user has at least one tenant (default)
    # Check if they have memberships now
    # If using lazy checking, we might skip this invalid query for now
    # But usually a user created cleanly has 0 memberships unless invited.
    
    # We will simply check if they have any memberships.
    # Note: associate_invitations commits, so they might have one now.
    
    # Re-fetch memberships
    # result = await db.execute(select(TenantMembership).where(TenantMembership.user_id == user.id))
    # if not result.scalars().first():
    #     # Create default tenant
    #     tenant_in = TenantCreate(name=f"{user.email}'s Org", slug=None, type="default")
    #     # reuse create_tenant logic or call service? 
    #     # For now, let's just leave it relying on them creating one via UI or being invited.
    #     # Actually, user expectation is usually a default workspace.
    #     pass

    # Send Welcome Email
    from app.services.email import EmailService
    # We can use background task here too if we inject it, but for now await/sync or use FastMail async
    await EmailService.send_welcome_email(user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
        secure=False 
    )

    return {
        "access": access_token,
        "refresh": refresh_token,
        "token_type": "bearer",
    }

@router.post("/token-refresh/", response_model=Token)
async def refresh_token_endpoint(
    response: Response,
    request: Request,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    Refresh access token using refresh token from cookie.
    """
    # Fallback to body or header if cookie missing? 
    # Typically secure flow uses cookie.
    if not refresh_token:
         # Try logic from body if needed, but for now stick to cookie
         pass
         
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    user_id = security.verify_token(refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user or not user.is_active:
         raise HTTPException(status_code=401, detail="User invalid")
         
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Optionally rotate refresh token
    new_refresh_token = security.create_refresh_token(user.id)
    
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
        secure=False 
    )
    
    return {
        "access": access_token,
        "refresh": new_refresh_token,
        "token_type": "bearer",
    }

@router.post("/logout/")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}
