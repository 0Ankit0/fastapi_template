from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from src.apps.organizations.api.v1.organization_members import _invalidate_org_members_cache
from src.apps.iam.services.policy_service import PolicyService
from src.apps.iam.models.user import User
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.organizations.schemas.organization_members import OrganizationMemberResponse, OrganizationMembershipInvitationRequest
from src.core.utils import encode_cursor
from src.core.exceptions import NotFoundError, ValidationError
from src.core.cache import RedisCache
from src.core.dependencies import DB, get_current_org, get_current_user, require_module_permission
from src.core.eums import OrganizationMemberStatus, RBACModule, RBACRole
from src.core.types import  HashId
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination
from src.db.query import select, or_, and_
import src.core.security as security
from src.apps.organizations.models import OrganizationMember, Organization
from src.core.logging import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

router = APIRouter(
    prefix="/organizations/members",
    tags=["Organization Members"],
)
PUBLIC_ORG_MEMBERS_RATE_LIMIT = limiter.limit("10/minute")

@router.get("/accept-invitation/", name="accept_invitation", status_code=status.HTTP_200_OK, response_model= ApiSuccessResponse[None])
@PUBLIC_ORG_MEMBERS_RATE_LIMIT
async def accept_invitation(
    db: DB,
    request: Request,
    t: str = Query(..., description="Invitation token to verify"),
) ->  ApiSuccessResponse[None]:
    """
    Verify the validity of an organization membership invitation token.
    """
    try:
        from src.apps.iam.models.used_token import UsedToken
        
        # Decrypt and verify the secure URL token
        try:
            token_data = security.verify_secure_url_token(t)
            logger.info(f"Token data extracted: {token_data}")
        except Exception:
            raise ValidationError(f"Invalid or expired accept invitation token.")
        
        logger.error(f"Token data: {token_data}")
        user_id = token_data.get("user_id")
        org_slug = token_data.get("org_slug")
        paseto_token = token_data.get("token")
        purpose = token_data.get("purpose")
        
        if not all([user_id, org_slug, paseto_token]) or purpose != "organization_invitation":
            raise ValidationError("Invalid invitation token data")
        
        if not isinstance(paseto_token, str) or not isinstance(user_id, (str, int)) or not isinstance(org_slug, (str, int)):
            raise ValidationError("Invalid token format")

        # Verify the embedded PASETO token
        payload = security.verify_token( paseto_token, token_type=security.TokenType.ORGANIZATION_INVITATION)
        token_jti = payload.get("jti")
        
        # Verify user_id matches
        if str(payload.get("sub")) != str(user_id):
            raise ValidationError("Token data mismatch - possible tampering detected")
        
        # Check if token has already been used
        if token_jti:
            used_check = await db.execute(
                select(UsedToken).where(UsedToken.token_jti == token_jti)
            )
            if used_check.scalars().first():
                raise ValidationError("This organization invitation link has already been used")
                
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise 
    
    try:
        organization_by_slug = await db.execute(select(Organization).where(Organization.slug == org_slug))
        org = organization_by_slug.scalar_one_or_none()
        if not org:
            raise NotFoundError("Organization not found for this invitation token")
        result = await db.execute(select(OrganizationMember).where(
            and_(
                OrganizationMember.user_id == int(user_id),
                OrganizationMember.organization_id == org.id,
                OrganizationMember.status == OrganizationMemberStatus.INVITED
            )
        ))
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValidationError("User not found for this invitation token")
        
        user.status = OrganizationMemberStatus.ACTIVE

        # Mark token as used
        if token_jti:
            used_token = UsedToken(
                token_jti=token_jti,
                user_id=int(user_id),
                token_purpose="organization_invitation"
            )
            db.add(used_token)
        
        await db.commit()
        
        # Invalidate all related caches
        await _invalidate_org_members_cache(user.organization_id)

        return ApiSuccessResponse[None](message="Organization invitation accepted successfully")
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise 
