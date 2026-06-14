from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.organizations.schemas.organization_members import OrganizationMemberResponse, OrganizationMembershipInvitationRequest
from src.core.utils import encode_cursor
from src.core.exceptions import NotFoundError, ValidationError
from src.core.cache import RedisCache
from src.core.dependencies import DB
from src.db.session import get_session
from src.core.eums import OrganizationMemberStatus, RBACModule
from src.apps.organizations.dependencies import get_current_org
from src.core.types import  HashId
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination
from src.db.query import select, or_, and_
import src.core.security as security
from src.apps.iam.dependencies import  get_current_user, require_module_permission

if TYPE_CHECKING:
    from src.apps.organizations.models import OrganizationMember, Organization
router = APIRouter(prefix="/organizations/members",
        tags=["Organization Members"],
        dependencies=[
            require_module_permission(RBACModule.ORGANIZATION_MEMBERS)
        ]
    )

async def _invalidate_org_members_cache(org_id: int):
    await RedisCache.clear_pattern(f"org:{org_id}:members:*")
    await RedisCache.clear_pattern(f"org:{org_id}:member:*")

@router.get("/", status_code=status.HTTP_200_OK, response_model=CursorPage[OrganizationMemberResponse])
async def list_organization_members(
    db: DB,
    pagination: CursorPagination = Depends(),
    org: str = Query(..., description="Organization slug to list members for"),
    search: str | None = Query(
        default=None,
        description="Search term to filter organization members by name or email",
    ),
    current_user=Depends(get_current_user)
):
    """
    List organization members with optional search and cursor pagination.
    """
    cache_key = (
        f"org:{org}:members:"
        f"{pagination.cursor}:"
        f"{pagination.limit}:"
        f"{search}"
    )
    cached_result = await RedisCache.get(cache_key)
    if cached_result:
        return cached_result
    
    # TODO: check if the user can access the current organization
    organization_by_slug = await db.execute(select(Organization).where(Organization.slug == org))
    organization = organization_by_slug.scalar_one_or_none()
    if not organization:
        raise NotFoundError(message="Organization not found")
    
    query = select(OrganizationMember).where(OrganizationMember.organization_id == organization.id)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                OrganizationMember.user.username.ilike(search_term),
                OrganizationMember.user.email.ilike(search_term)
            )
        )
    query = (
        query
        .order_by(OrganizationMember.id)
        .limit(pagination.limit + 1)
    )

    result = await db.execute(query)
    members = result.scalars().all()

    has_next_page = (
        len(members) > pagination.limit
    )
    if has_next_page:
        members = members[:pagination.limit]

    items = [
        OrganizationMemberResponse.model_validate(member)
        for member in members
    ]
    next_cursor = None

    if has_next_page and members:
        next_cursor = encode_cursor(
            members[-1].id
        )

    response = CursorPage[OrganizationMemberResponse](
        items=items,
        next_cursor=next_cursor
    )
    await RedisCache.set(
        cache_key, 
        response.model_dump_json(),
        ttl=120
    )
    return response

@router.get("/{member_id}", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[OrganizationMemberResponse])
async def get_organization_member(
    db: DB,
    member_id: HashId,
    org: str = Query(..., description="Organization slug to list members for"),
    current_user=Depends(get_current_user)
) -> ApiSuccessResponse[OrganizationMemberResponse]:
    """
    Get details of a specific organization member by their ID.
    """
    cache_key = f"org:{org}:member:{member_id}"
    cached_result = await RedisCache.get(cache_key)
    if cached_result:
        return ApiSuccessResponse[OrganizationMemberResponse](
            message="Organization member retrieved successfully",
            data=OrganizationMemberResponse.model_validate_json(cached_result)
        )
    
    organization_by_slug = await db.execute(select(Organization).where(Organization.slug == org))
    organization = organization_by_slug.scalar_one_or_none()
    if not organization:
        raise NotFoundError(message="Organization not found")
    
    query = select(OrganizationMember).where(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.id == member_id
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(message="Organization member not found")
    
    response = OrganizationMemberResponse.model_validate(member)
    await RedisCache.set(
        cache_key, 
        response.model_dump_json(),
        ttl=120
    )
    return ApiSuccessResponse[OrganizationMemberResponse](
        message="Organization member retrieved successfully",
        data=response
    )

@router.post("/{member_id}/resend-invite", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[OrganizationMemberResponse])
async def resend_invite(
    invite_request: OrganizationMembershipInvitationRequest,
    db: DB,
    current_user=Depends(get_current_user)
) -> ApiSuccessResponse[OrganizationMemberResponse]:
    """
    Resend an invitation email to a specific organization member by their ID.
    """

    # TODO: check if the user can access the current organization
    query = select(OrganizationMember).where(
        OrganizationMember.organization_id == invite_request.organization_id,
        OrganizationMember.id == invite_request.member_id
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(message="Organization member not found")
    
    if member.status != OrganizationMemberStatus.INVITED:
        raise ValidationError(message="Only invited members can be resent an invitation")
    
    from src.apps.organizations.services.email import OrganizationEmailService
    invitation_token = security.create_organization_invitation_token(
        subject=member.user.id,
        Organization=str(member.organization_id)
    )
    await OrganizationEmailService.send_member_invitation_email(
        member.user,
        token=invitation_token,
        organization_name=member.organization.name
    )
    invitation_token_tracking = TokenTracking(
        user_id=member.user.id,
        token_jti=str(uuid4()),
        token_type=security.TokenType.ORGANIZATION_INVITATION.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
    )
    db.add(invitation_token_tracking)
    await db.commit()

    response = OrganizationMemberResponse.model_validate(member)
    return ApiSuccessResponse[OrganizationMemberResponse](
        message="Invitation resent successfully",
        data=response
    )

@router.get("/accept-invitation/", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[OrganizationMemberResponse] | ApiSuccessResponse[None])
async def accept_invitation(
    db: DB,
    t: str = Query(..., description="Invitation token to verify"),
) -> ApiSuccessResponse[OrganizationMemberResponse] | ApiSuccessResponse[None]:
    """
    Verify the validity of an organization membership invitation token.
    """
    try:
        from src.apps.iam.models.used_token import UsedToken
        
        # Decrypt and verify the secure URL token
        try:
            token_data = security.verify_secure_url_token(t)
        except Exception:
            raise ValidationError("Invalid or expired reset token")
        
        user_id = token_data.get("user_id")
        organization_id = token_data.get("organization_id")
        paseto_token = token_data.get("token")
        purpose = token_data.get("purpose")
        
        if not all([user_id, organization_id, paseto_token]) or purpose != "organization_invitation":
            raise ValidationError("Invalid invitation token data")
        
        if not isinstance(paseto_token, str) or not isinstance(user_id, (str, int)) or not isinstance(organization_id, (str, int)):
            raise ValidationError("Invalid token format")

        # Verify the embedded PASETO token
        payload = security.verify_token( paseto_token, token_type=security.TokenType.PASSWORD_RESET)
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
        raise ValidationError("Invalid or expired invitation token")
    
    try:
        result = await db.execute(select(OrganizationMember).where(
            and_(
                OrganizationMember.user_id == int(user_id),
                OrganizationMember.organization_id == int(organization_id),
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

        return ApiSuccessResponse[None](message="Password has been reset successfully")
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during password reset"
        )

 

@router.delete("/{member_id}", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[None])
async def remove_organization_member(
    member_id: HashId,
    db: DB,
    org: str = Query(..., description="Organization slug to list members for"),
    current_user=Depends(get_current_user)
) -> ApiSuccessResponse[None]:
    """
    Remove a specific organization member by their ID.
    """
    # TODO: check if the user can access the current organization
    query = select(Organization).where(Organization.slug == org)
    result = await db.execute(query)
    organization = result.scalar_one_or_none()
    if not organization:
        raise NotFoundError(message="Organization not found")
    
    query = select(OrganizationMember).where(
        OrganizationMember.organization_id == organization.id,
        OrganizationMember.id == member_id
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(message="Organization member not found")
    
    # TODO: For the user and organization remove it from the cache as well as the casbin rules
    await _invalidate_org_members_cache(organization.id)
    await db.delete(member)
    await db.commit()

    return ApiSuccessResponse[None](
        message="Organization member removed successfully",
        data=None
    )
