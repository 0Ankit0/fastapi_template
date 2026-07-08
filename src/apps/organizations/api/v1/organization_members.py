from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query, Request, status
from src.apps.iam.models.user import User
from src.apps.organizations.schemas.organization_members import OrganizationMemberResponse, OrganizationMembershipInvitationRequest
from src.core.dependencies import DB, get_current_org, get_current_user, require_module_permission
from src.core.enums import OrganizationMemberStatus, RBACModule
from src.core.types import  HashId
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination
from src.apps.organizations.models import OrganizationMember, Organization
from src.core.logging import get_logger
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.core.pagination import CursorSortDirection
from src.apps.organizations.services.organization_members import organization_members_service
from src.apps.iam.services.policy_service import PolicyService

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

@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=CursorPage[OrganizationMemberResponse],
    summary="List Organization Members",
    description="Cursor-paginated organization member listing with search, status filter, and directional sorting.",
)
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
    member_status: OrganizationMemberStatus | None = Query(
        default=None,
        description="Filter members by membership status",
    ),
    sort_direction: CursorSortDirection = Query(
        default=CursorSortDirection.ASC,
        description="Sort by member id asc/desc",
    ),
):
    """
    List organization members with optional search and cursor pagination.
    """
    return await organization_members_service.list_organization_members(
        db,
        org=org,
        pagination=pagination,
        search=search,
        member_status=member_status,
        sort_direction=sort_direction,
    )

@router.get(
    "/{member_id}",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[OrganizationMemberResponse],
    summary="Get organization member",
    description="Returns a single organization membership record together with the resolved role mapping.",
)
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
    return await organization_members_service.get_organization_member(
        db,
        org=org,
        member_id=member_id,
    )

@router.get(
    "/{member_id}/add",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[None],
    deprecated=True,
    summary="Add Organization Member (Deprecated GET)",
    description="Deprecated compatibility alias for the member invite action. Use POST endpoint instead.",
)
@router.post(
    "/{member_id}/add",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[None],
    summary="Add Organization Member",
    description="Creates an invited membership for an existing user and dispatches invitation email.",
)
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
    return await organization_members_service.add_member(
        db,
        member_id=member_id,
        current_user=current_user,
        org=org,
        request=request,
    )

@router.get(
    "/invite",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[None],
    deprecated=True,
    summary="Invite Organization Member (Deprecated GET)",
    description="Deprecated compatibility alias for invitation creation. Use POST endpoint instead.",
)
@router.post(
    "/invite",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[None],
    summary="Invite Organization Member",
    description="Invites a user by email and creates token tracking for invitation acceptance.",
)
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
    return await organization_members_service.invite_member(
        db,
        data=data,
        org=org,
        request=request,
    )

@router.get(
    "/{member_id}/resend-invite",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[OrganizationMemberResponse],
    deprecated=True,
    summary="Resend Member Invitation (Deprecated GET)",
    description="Deprecated compatibility alias for invitation resend. Use POST endpoint instead.",
)
@router.post(
    "/{member_id}/resend-invite",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[OrganizationMemberResponse],
    summary="Resend Member Invitation",
    description="Reissues invitation email for an invited organization member.",
)
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
    return await organization_members_service.resend_invite(
        db,
        member_id=member_id,
        org=org,
        request=request,
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
    return await organization_members_service.remove_member(
        db,
        member_id=member_id,
        org=org,
    )
