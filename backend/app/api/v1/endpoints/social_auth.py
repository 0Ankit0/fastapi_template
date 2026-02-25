from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.api import deps
from app.db.session import AsyncSession
from app.models.user import User, UserProfile
from app.core import security
from app.services.tenant_service import TenantService
from app.services.email import EmailService
from sqlmodel import select
from datetime import timedelta
import logging

try:
    from fastapi_sso.sso.google import GoogleSSO
    from fastapi_sso.sso.facebook import FacebookSSO
except ImportError:
    GoogleSSO = None
    FacebookSSO = None

router = APIRouter()

logger = logging.getLogger(__name__)

# Initialize SSO instances
google_sso = GoogleSSO(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    redirect_uri=f"{settings.SERVER_HOST}{settings.API_V1_STR}/social/google/callback",
    allow_insecure_http=True,
    scope=["openid", "email", "profile"]
) if GoogleSSO and settings.GOOGLE_CLIENT_ID else None

facebook_sso = FacebookSSO(
    client_id=settings.FACEBOOK_CLIENT_ID,
    client_secret=settings.FACEBOOK_CLIENT_SECRET,
    redirect_uri=f"{settings.SERVER_HOST}{settings.API_V1_STR}/social/facebook/callback",
    allow_insecure_http=True,
    scope=["email", "public_profile"]
) if FacebookSSO and settings.FACEBOOK_CLIENT_ID else None

@router.get("/google/login")
async def google_login():
    if not google_sso:
        raise HTTPException(status_code=500, detail="Google SSO not configured")
    return await google_sso.get_login_redirect()

@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(deps.get_db)):
    if not google_sso:
        raise HTTPException(status_code=500, detail="Google SSO not configured")
    
    try:
        user_info = await google_sso.verify_and_process(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return await process_social_login(db, user_info, "google")

@router.get("/facebook/login")
async def facebook_login():
    if not facebook_sso:
        raise HTTPException(status_code=500, detail="Facebook SSO not configured")
    return await facebook_sso.get_login_redirect()

@router.get("/facebook/callback")
async def facebook_callback(request: Request, db: AsyncSession = Depends(deps.get_db)):
    if not facebook_sso:
        raise HTTPException(status_code=500, detail="Facebook SSO not configured")
    
    try:
        user_info = await facebook_sso.verify_and_process(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return await process_social_login(db, user_info, "facebook")

async def process_social_login(db: AsyncSession, user_info, provider: str):
    email = user_info.email
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by social provider")
        
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        # Create user
        # Password? Set unguessable one or mark as social user.
        # We can just set a random high-entropy password.
        import secrets
        random_password = secrets.token_urlsafe(32)
        
        user = User(
            email=email,
            hashed_password=security.get_password_hash(random_password),
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create Profile
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.commit()
        
        # Associate Invitations & Default Tenant
        await TenantService.associate_invitations(db, email, user.id)
        # TODO: Create default tenant if none check logic (reused from Auth endpoint)
        # For now, just rely on associate. 
        
        # Send Welcome Email
        await EmailService.send_welcome_email(user)
        
    # Create Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    # Redirect to frontend with token
    # Security note: Passing token in URL fragment is standard for implicit-like flows but 
    # setting HttpOnly cookies is better. For this template, we follow the pattern of returning token or redirecting.
    # The frontend expects a redirect? 
    # Usually social auth redirects back to frontend /auth/callback?token=...
    
    frontend_url = settings.FRONTEND_URL
    redirect_url = f"{frontend_url}/auth/callback?access_token={access_token}"
    
    response = RedirectResponse(url=redirect_url)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        samesite="lax",
        secure=False 
    )
    return response
