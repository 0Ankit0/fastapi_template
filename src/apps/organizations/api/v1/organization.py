from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from src.core.types import HashId
from src.apps.iam.models.user import User
from src.apps.organizations.schemas.organization import OrganizationPartialUpdate, OrganizationResponse, OrganizationCreate, OrganizationUpdate
from src.core.dependencies import DB, get_current_active_superuser, require_module_permission
from src.core.schemas import CursorPage, CursorPagination, ApiSuccessResponse
from src.core.enums import OrganizationStatus, RBACModule
from src.core.pagination import CursorSortDirection
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.apps.organizations.services.organizations import organization_service

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(
    prefix="/organizations/{org}", 
    tags=["Organizations"],
    dependencies=[
        Depends(require_module_permission(RBACModule.ORGANIZATIONS))
    ]
)
ORGANIZATION_RATE_LIMIT = limiter.limit("10/minute")


@router.get(
    "/",
    response_model=CursorPage[OrganizationResponse],
    summary="List Organizations",
    description="Cursor-paginated organization listing with search, status, owner filters, and directional sorting.",
)
@ORGANIZATION_RATE_LIMIT
async def list_organizations(
   db: DB,
   request: Request,
   pagination: CursorPagination = Depends(),
   search: str | None = Query(
      default=None,
        description="Search term to filter organizations by name or description",
   ),
   org_status: OrganizationStatus | None = Query(
      default=None,
      description="Filter organizations by status"
   ),
    owner_id: HashId | None = Query(default=None, description="Filter organizations by owner"),
    sort_direction: CursorSortDirection = Query(
        default=CursorSortDirection.DESC,
        description="Sort by newest or oldest organization",
    ),
):
    """
    List organizations with optional search and cursor pagination.
    """
    return await organization_service.list_organizations(
        db,
        pagination=pagination,
        search=search,
        org_status=org_status,
        owner_id=owner_id,
        sort_direction=sort_direction,
    )

@router.get(
    "/{org_id}",
    response_model=ApiSuccessResponse[OrganizationResponse],
    summary="Get organization",
    description="Returns a single organization record by its public identifier.",
)
@ORGANIZATION_RATE_LIMIT
async def get_organization(
    org_id: HashId,
    request: Request,
    db: DB,
):
    """
    Get organization details by ID.
    """
    return await organization_service.get_organization(db, org_id=org_id)


@router.post(
    "/",
    response_model=ApiSuccessResponse[OrganizationResponse],
    summary="Create organization",
    description="Creates a new organization with the authenticated superuser as owner and creator.",
)
@ORGANIZATION_RATE_LIMIT
async def create_organization(
    org_data: OrganizationCreate,
    db: DB,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_superuser)],
):
    """
    Create a new organization.
    """
    return await organization_service.create_organization(
        db,
        org_data=org_data,
        current_user_id=current_user.id,
    )


@router.put(
    "/{org_id}",
    response_model=ApiSuccessResponse[OrganizationResponse],
    summary="Update organization",
    description="Updates the core organization fields for the requested organization.",
)
@ORGANIZATION_RATE_LIMIT
async def update_organization(
    org_id: HashId,
    request: Request,
    org_data: OrganizationUpdate,
    db: DB,
):
    """
    Update an existing organization.
    """
    return await organization_service.update_organization(
        db,
        org_id=org_id,
        org_data=org_data,
    )


@router.patch(
    "/{org_id}",
    response_model=ApiSuccessResponse[OrganizationResponse],
    summary="Patch organization",
    description="Partially updates an organization record.",
)
@ORGANIZATION_RATE_LIMIT
async def partial_update_organization(
    org_id: HashId,
    request: Request,
    org_data: OrganizationPartialUpdate,
    db: DB,
):
    """
    Partially update an existing organization.
    """
    return await organization_service.partial_update_organization(
        db,
        org_id=org_id,
        org_data=org_data,
    )

@router.delete("/{org_id}", response_model=ApiSuccessResponse[None])
@ORGANIZATION_RATE_LIMIT
async def delete_organization(
   org_id: HashId,
   request: Request,
   db: DB ,
   _ = Depends(get_current_active_superuser)
):
    """
    Delete an organization by ID.
    """
    return await organization_service.delete_organization(db, org_id=org_id)