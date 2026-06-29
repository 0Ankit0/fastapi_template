from __future__ import annotations

from typing import Annotated, AsyncGenerator, Optional
from fastapi import status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, Path, Request
from src.core.config import settings
from src.core.exceptions import AuthenticationError, AuthorizationError, NotFoundError, ValidationError
from src.core import security
from src.db.query import select, selectinload
from src.apps.iam.schemas.token import TokenPayload
from src.apps.organizations.models.organization import Organization
from src.apps.iam.models import TokenTracking
from src.apps.iam.models.user import User
from src.apps.organizations.models.organization import Organization
from src.core.exceptions import NotFoundError
from src.db.session import get_session 
from src.apps.iam.casbin import enforcer
from src.core.enums import RBACAction as Action, RBACModule as Module, UserStatus

DB = Annotated[AsyncSession, Depends(get_session)]


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

async def authenticate_token(
    token: str,
    db: DB,
) -> User:
    payload = security.decode_token(token)
    token_data = TokenPayload(**payload)

    if not token_data.sub:
        raise AuthorizationError(
            message="Token payload missing subject"
        )

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

    return user

async def get_current_user(
    request: Request,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(_bearer_scheme)
    ],
    db: DB,
) -> User:

    token = credentials.credentials if credentials else None

    if not token:
        token = request.cookies.get(
            settings.ACCESS_TOKEN_COOKIE_NAME
        )

    if not token:
        raise AuthenticationError(
            message="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await authenticate_token(
        token=token,
        db=db,
    )

    request.state.current_user_id = user.id

    return user  
   

async def get_current_active_superuser(
current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if not current_user.is_superuser and not current_user.status == UserStatus.ACTIVE:
        raise AuthorizationError(
            message="Insufficient permissions"
        )
    return current_user

CurrentUser = Annotated[User, Depends(get_current_user)]

async def get_current_org(
    db: DB,
    current_user: CurrentUser,
    org: Annotated[str, Path(description="Organization slug")],
) -> Organization | None:
    """
    Get the current organization based on the org slug query parameter and user membership
    """
    try:
        if not org:
            raise NotFoundError("Organization slug is required")
        
        if current_user.is_superuser:
            if org == "global":
                return None
            
            result = await db.execute(
                select(Organization).where(Organization.slug == org)
            )
            organization = result.scalars().first()
            if not organization:
                raise NotFoundError("Organization not found")
            return organization
        
        # Check if the user is a member of the specified organization
        result = await db.execute(
            select(Organization).where(
                Organization.slug == org,
                Organization.members.any(id=current_user.id)
            )
        )
        organization = result.scalars().first()
        
        if not organization:
            raise NotFoundError("Organization not found or access denied")
        
        return organization
    except Exception:
        raise 

CurrentOrg = Annotated[Organization, Depends(get_current_org)]
 
def require_module_permission(module: Module):
    async def checker(
        request: Request,
        current_user: CurrentUser,
        org: CurrentOrg,
    ):
        if current_user.is_superuser:
            return

        action = METHOD_ACTION_MAP[request.method]

        allowed = enforcer.enforce(
            current_user.id,
            org.id,
            module.value,
            action.value,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    return checker