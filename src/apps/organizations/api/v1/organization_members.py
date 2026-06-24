from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Annotated
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
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

limiter = Limiter(key_func=get_remote_address)
logger = get_logger(__name__)

router = APIRouter(
    prefix="/organizations/{org}/members",
    tags=["Organization Members"],
    dependencies=[
        Depends(require_module_permission(RBACModule.ORGANIZATION_MEMBERS))
    ]
)

ORGANIZATION_MEMBERS_RATE_LIMIT = limiter.limit("10/minute")
CurrentOrg = Annotated[Organization, Depends(get_current_org)]
CurrentUser = Annotated[User, Depends(get_current_user)]

async def _invalidate_org_members_cache(org_id: int):
    await RedisCache.clear_pattern(f"org:{org_id}:members:*")
    await RedisCache.clear_pattern(f"org:{org_id}:member:*")

@router.get("/", status_code=status.HTTP_200_OK, response_model=CursorPage[OrganizationMemberResponse])
@ORGANIZATION_MEMBERS_RATE_LIMIT
async def list_organization_members(
    db: DB,
    request: Request,
    org: CurrentOrg,
    pagination: CursorPagination = Depends(),
    search: str | None = Query(
        default=None,
        description="Search term to filter organization members by name or email",
    ),
):
    """
    List organization members with optional search and cursor pagination.
    """
    cache_key = (
        f"org:{org.id}:members:"
        f"{pagination.cursor}:"
        f"{pagination.limit}:"
        f"{search}"
    )
    cached_result = await RedisCache.get(cache_key)
    if cached_result:
        return cached_result
    
    
    query = select(OrganizationMember).where(OrganizationMember.organization_id == org.id)

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

    role_map = PolicyService.get_org_roles(org.slug)

    items = [
        OrganizationMemberResponse(
            **OrganizationMemberResponse.model_validate(
                member
            ).model_dump(exclude={"role"}),
            role=role_map.get(member.user_id, [])
        )
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
@ORGANIZATION_MEMBERS_RATE_LIMIT
async def get_organization_member(
    db: DB,
    request: Request,
    member_id: HashId,
    org: CurrentOrg,
) -> ApiSuccessResponse[OrganizationMemberResponse]:
    """
    Get details of a specific organization member by their ID.
    """
    cache_key = f"org:{org.id}:member:{member_id}"
    cached_result = await RedisCache.get(cache_key)
    if cached_result:
        return ApiSuccessResponse[OrganizationMemberResponse](
            message="Organization member retrieved successfully",
            data=OrganizationMemberResponse.model_validate_json(cached_result)
        )
    
    
    query = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == member_id
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(message=f"Organization member not found for org")
    
    response = OrganizationMemberResponse(
        **OrganizationMemberResponse.model_validate(member)
        .model_dump(exclude={"role"}
        )   
    )
    response.role = PolicyService.get_user_roles(member_id, org.slug)
    await RedisCache.set(
        cache_key, 
        response,
        ttl=120
    )
    return ApiSuccessResponse[OrganizationMemberResponse](
        message="Organization member retrieved successfully",
        data=response
    )

@router.get("/{member_id}/add", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[None])
@ORGANIZATION_MEMBERS_RATE_LIMIT
async def add_member(
    member_id: Annotated[HashId, Path(description="ID of the user to add as an organization member")],
    db: DB,
    current_user: CurrentUser,
    org: CurrentOrg,
    request: Request
) -> ApiSuccessResponse[None]:
    """
    Add a specific user as an organization member by their ID.
    """
    query = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == member_id
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    if member:
        raise ValidationError(message="User is already a member of the organization")
    
    user_query = select(User).where(User.id == member_id)
    result = await db.execute(user_query)
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(message="User not found")

    organization_member = OrganizationMember(
        user_id=member_id,
        organization_id=org.id,
        status=OrganizationMemberStatus.INVITED,
        invited_by=current_user.id,
        joined_at=datetime.now(timezone.utc)
    )
    db.add(organization_member)
    await db.commit()
    await db.refresh(organization_member)

    from src.apps.organizations.services.email import OrganizationEmailService
    invitation_token = security.create_organization_invitation_token(
        subject=member_id,
        Organization=str(org.id)
    )
    await OrganizationEmailService.send_member_invitation_email(
        user=user,
        url= request.url_for("accept_invitation"),
        email=user.email,
        token=invitation_token,
        org_slug=org.slug
    )

    invitation_token_tracking = TokenTracking(
        user_id=user.id,
        token_jti=str(uuid4()),
        user_agent=request.headers.get("user-agent") or '',
        ip_address=request.client.host if request.client else None,
        token_type=security.TokenType.ORGANIZATION_INVITATION.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
    )
    db.add(invitation_token_tracking)
    await db.commit()

    return ApiSuccessResponse[None](
        message="Organization member invited successfully",
        data=None
    )

@router.get("/invite", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[None])
@ORGANIZATION_MEMBERS_RATE_LIMIT
async def invite_member(
    data: OrganizationMembershipInvitationRequest,
    db: DB,
    org: CurrentOrg,
    request: Request
) -> ApiSuccessResponse[None]:
    """
    Send an invitation email to an unknown user using their email address to join the organization as a member.
    """
    from src.apps.iam.models.user import User
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    
    if user:
        # If the user already exists, we can directly add them as a member
        organization_member = OrganizationMember(
            user_id=user.id,
            organization_id=org.id,
            role=data.role,
            status=OrganizationMemberStatus.ACTIVE
        )
        db.add(organization_member)
        await db.commit()
        # return ApiSuccessResponse[None](
        #     message="Organization member added successfully",
        #     data=None
        # )
    
    # For new users, we create an invitation token and send an email
    from src.apps.organizations.services.email import OrganizationEmailService
    invitation_token = security.create_organization_invitation_token(
        subject=data.email,
        Organization=str(org.id)
    )
    await OrganizationEmailService.send_member_invitation_email(
        user=None,
        url= request.url_for("accept_invitation"),
        email=data.email,
        token=invitation_token,
        org_slug=org.slug
    )

    invitation_token_tracking = TokenTracking(
        user_id=None,
        token_jti=str(uuid4()),
        user_agent=request.headers.get("user-agent") or '',
        ip_address=request.client.host if request.client else None,
        token_type=security.TokenType.ORGANIZATION_INVITATION.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
    )
    db.add(invitation_token_tracking)
    await db.commit()

    return ApiSuccessResponse[None](
        message="Organization member invited successfully",
        data=None
    )

@router.get("/{member_id}/resend-invite", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[OrganizationMemberResponse])
@ORGANIZATION_MEMBERS_RATE_LIMIT
async def resend_invite(
    member_id: Annotated[HashId, Path(description="ID of the organization member to resend the invitation to")],
    db: DB,
    org: CurrentOrg,
    request: Request
) -> ApiSuccessResponse[OrganizationMemberResponse]:
    """
    Resend an invitation email to a specific organization member by their ID.
    """

    query = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == member_id
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
        user=member.user,
        url=request.url_for("accept_invitation"),
        email=None,
        token=invitation_token,
        org_slug=member.organization.slug
    )
    invitation_token_tracking = TokenTracking(
        user_id=member.user.id,
        token_jti=str(uuid4()),
        user_agent=request.headers.get("user-agent") or '',
        ip_address=request.client.host if request.client else None,
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

@router.delete("/{member_id}", status_code=status.HTTP_200_OK, response_model=ApiSuccessResponse[None])
@ORGANIZATION_MEMBERS_RATE_LIMIT
async def remove_organization_member(
    member_id: HashId,
    db: DB,
    request: Request,
    org: CurrentOrg,
) -> ApiSuccessResponse[None]:
    """
    Remove a specific organization member by their ID.
    """
    
    query = select(OrganizationMember).where(
        OrganizationMember.organization_id == org.id,
        OrganizationMember.user_id == member_id
    )
    result = await db.execute(query)
    member = result.scalar_one_or_none()
    if not member:
        raise NotFoundError(message="Organization member not found")
    
    PolicyService.remove_user_with_roles(
        member_id,
        org.slug,
    )
    
    await _invalidate_org_members_cache(org.id)
    await db.delete(member)
    await db.commit()

    return ApiSuccessResponse[None](
        message="Organization member removed successfully",
        data=None
    )
