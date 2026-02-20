from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.core.config import settings
from src.apps.core import security
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User, UserProfile
from src.apps.iam.schemas.token import Token
from src.apps.iam.schemas.user import LoginRequest, UserCreate

router = APIRouter()

@router.post("/login/",response_model=Token | None)
async def login_access_token(
    response: Response,
    set_cookie: bool,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    result = await db.execute(
        select(User).where(User.username == login_data.username) # type: ignore
    )
    user = result.scalars().first()

    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    if set_cookie:
        response.set_cookie(
            key=settings.ACCESS_TOKEN_COOKIE,
            value=access_token,
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    else:
        return Token(
            access=access_token,
            refresh=refresh_token,
            token_type="bearer"
        )
    
@router.post("/logout/")
async def logout(
    response: Response
) -> Any:
    """
    Logout user by clearing the access token cookie
    """
    response.delete_cookie(key=settings.ACCESS_TOKEN_COOKIE)
    return {"message": "Successfully logged out"}

@router.post("/signup/", response_model=Token | None)
async def signup(
    response: Response,
    set_cookie: bool,
    login_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Create a new user account
    """
    result = await db.execute(
        select(User).where(User.username == login_data.username) # type: ignore
    )
    user = result.scalars().first()

    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    hashed_password = security.get_password_hash(login_data.password)
    new_user = User(
       username=login_data.username,
       email=login_data.email,
        hashed_password=hashed_password,
        profile=None
    )
    user_profile = UserProfile(
        first_name=login_data.first_name or "",
        last_name=login_data.last_name or "",
        phone=login_data.phone or "",
        user=new_user
    )
    
    db.add(new_user)
    db.add(user_profile)
    await db.commit()

    from src.apps.iam.services.email import EmailService
    await EmailService.send_welcome_email(user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        new_user.id, expires_delta=access_token_expires
    )
    
    refresh_token = security.create_refresh_token(new_user.id)

    if set_cookie:
        response.set_cookie(
            key=settings.ACCESS_TOKEN_COOKIE,
            value=access_token,
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    else:
        return Token(
            access=access_token,
            refresh=refresh_token,
            token_type="bearer"
        )

@router.post("/refresh/", response_model=Token | None)
async def refresh_token(
    response: Response,
    request: Request,
    set_cookie: bool,
    refresh_token: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Refresh access token using a valid refresh token
    """
    if not refresh_token:
        refresh_token = request.cookies.get(settings.REFRESH_TOKEN_COOKIE)
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    user_id = security.verify_token(refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    result = await db.execute(select(User).where(User.id == user_id)) # type: ignore
    user = result.scalars().first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    new_refresh_token = security.create_refresh_token(user.id)

    if set_cookie:
        response.set_cookie(
            key=settings.ACCESS_TOKEN_COOKIE,
            value=access_token,
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        response.set_cookie(
            key=settings.REFRESH_TOKEN_COOKIE,
            value=new_refresh_token,
            httponly=True,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )
    else:
        return Token(
            access=access_token,
            refresh=new_refresh_token,
            token_type="bearer"
        )