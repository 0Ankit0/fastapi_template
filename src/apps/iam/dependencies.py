from __future__ import annotations
from typing import TYPE_CHECKING, AsyncGenerator

from typing import Annotated, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from alembic.util import status
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from apps.iam.schemas.token import TokenPayload
from core import security
from core.exceptions import AuthenticationError, AuthorizationError, ValidationError
from src.core.config import settings
from apps.iam.models.user import User
from core.dependencies import DB
from sqlalchemy.orm import selectinload
from db.session import get_session
from .casbin import enforcer
from fastapi import Request
from fastapi import status 
from db.query import select
from src.core.eums import RBACAction as Action, RBACModule as Module, UserStatus

from iam.models import TokenTracking

METHOD_ACTION_MAP = {
    "GET": Action.READ,
    "POST": Action.CREATE,
    "PUT": Action.UPDATE,
    "PATCH": Action.UPDATE,
    "DELETE": Action.DELETE,
}

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


# HTTPBearer with auto_error=False so cookie fallback still works,
# but FastAPI registers the BearerAuth security scheme on all
# routes that depend on get_current_user — enabling the Swagger
# "Authorize" button and lock icons on protected endpoints.
_bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer_scheme)],
    db: DB = Depends(get_db)
    ) -> User:
    # Prefer the Authorization: Bearer header (captured by HTTPBearer above),
    # fall back to the access_token cookie for browser-based clients.
    token: Optional[str] = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE_NAME)

    if not token:
        raise AuthenticationError(
            message="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        payload = security.decode_token(token)
        token_data = TokenPayload(**payload)
    except (security.TokenValidationError, ValidationError):
        raise AuthorizationError(
            message="Could not validate credentials",
        )
    
    if not token_data.sub:
        raise AuthorizationError(
            message="Token payload missing subject",
        )
    
    # Check if token is tracked and active
    jti = payload.get("jti")
    if jti:
        token_result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.token_jti == jti,
                TokenTracking.is_active
            )
        )
        token_tracking = token_result.scalars().first()
        
        if not token_tracking:
            raise AuthenticationError(
                message="Token is invalid or has been revoked",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.profile)
        )
        .where(User.id == int(token_data.sub))
    )
    user = result.scalars().first()

    if not user:
        raise AuthenticationError(
            message="User not found"
        )
    
    if user.status != UserStatus.ACTIVE:
        raise AuthenticationError(
            message="User account is inactive"
        )

    request.state.current_user_id = user.id
    return user

def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_superuser and not current_user.status == UserStatus.ACTIVE:
        raise AuthorizationError(
            message="Insufficient permissions"
        )
    return current_user

def require_module_permission(module: Module):
    async def checker(request: Request):
        # TODO: Extract user and org info from token payload
        payload = request.state.token_payload

        user_id = payload["sub"]
        org_id = payload["organization_id"]

        action = METHOD_ACTION_MAP[request.method]

        allowed = enforcer.enforce(
            user_id,
            org_id,
            module.value,
            action.value,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    return Depends(checker)