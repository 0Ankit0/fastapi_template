from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from src.core.types import HashId
from src.apps.iam.models.user import User
from src.core.exceptions import NotFoundError
from src.apps.organizations.models.organization import Organization
from src.apps.organizations.schemas.organization import OrganizationPartialUpdate, OrganizationResponse, OrganizationCreate, OrganizationUpdate
from src.db.query import select, or_
from src.core.utils import decode_cursor, encode_cursor
from src.core.dependencies import DB, get_current_active_superuser, require_module_permission
from src.core.schemas import CursorPage, CursorPagination, ApiSuccessResponse
from src.core.enums import OrganizationStatus, RBACModule
from src.core.cache import RedisCache
from slugify import slugify
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(
    prefix="/organizations/{org}", 
    tags=["Organizations"],
    dependencies=[
        Depends(require_module_permission(RBACModule.ORGANIZATIONS))
    ]
)
ORGANIZATION_RATE_LIMIT = limiter.limit("10/minute")

async def _invalidate_org_cache(org_id: int):
   await RedisCache.delete(f"org:{org_id}")
   await RedisCache.clear_pattern(f"org:{org_id}:*")


@router.get("/", response_model=CursorPage[OrganizationResponse])
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
):
    """
    List organizations with optional search and cursor pagination.
    """
    cache_key = (
      f"org:list:"
      f"{pagination.cursor}:"
      f"{pagination.limit}:"
      f"{search}"
    )
    cached_result = await RedisCache.get(cache_key)
    if cached_result:
      return cached_result
   
    query = select(Organization)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Organization.name.ilike(search_term),
                Organization.description.ilike(search_term)
            )
        )
    if org_status is not None:
        query = query.where(Organization.status == org_status)

    if pagination.cursor:
       _, cursor_id = decode_cursor(pagination.cursor)
       query = query.where(Organization.id > int(cursor_id))

    query = (
        query
        .order_by(Organization.id)
        .limit(pagination.limit + 1)  # Fetch one extra for pagination
    )

    result = await db.execute(query)
    organizations = result.scalars().all()

    has_next_page = (
       len(organizations) > pagination.limit
    )
    if has_next_page:
       organizations = organizations[:pagination.limit]

    items =[
       OrganizationResponse.model_validate(org)
       for org in organizations
    ]
    next_cursor = None

    if has_next_page and organizations:
       next_cursor = encode_cursor(
          organizations[-1].id
    )

    response = CursorPage[OrganizationResponse](
       items=items,
       next_cursor=next_cursor,
    )

    await RedisCache.set(
       cache_key,
       response.model_dump_json(),
       ttl=120
    )
    return response

@router.get("/{org_id}", response_model=ApiSuccessResponse[OrganizationResponse])
@ORGANIZATION_RATE_LIMIT
async def get_organization(
   org_id: HashId,
   request: Request,
   db: DB 
):
    """
    Get organization details by ID.
    """
    cache_key = f"org:{org_id}"
    cached_org = await RedisCache.get(cache_key)
    if cached_org:
       return ApiSuccessResponse[OrganizationResponse](
           message="Organization retrieved successfully",
           data=OrganizationResponse.model_validate_json(cached_org)
         )

    query = select(Organization).where(Organization.id == org_id)
    result = await db.execute(query)
    organization = result.scalar_one_or_none()

    if not organization:
        raise NotFoundError(message="Organization not found")

    org_response = OrganizationResponse.model_validate(organization)
    await RedisCache.set(
       cache_key,
       org_response.model_dump_json(),
       ttl=300
    )
    return ApiSuccessResponse[OrganizationResponse](
        message="Organization retrieved successfully",
        data=org_response
    )

@router.post("/", response_model=ApiSuccessResponse[OrganizationResponse])
@ORGANIZATION_RATE_LIMIT
async def create_organization(
   org_data: OrganizationCreate,
   db: DB,
   request: Request,
   current_user:Annotated[User, Depends(get_current_active_superuser)],
):
    """
    Create a new organization.
    """
    new_org = Organization(
        name=org_data.name,
        slug=slugify(org_data.name),
        description=org_data.description,
        status=OrganizationStatus.ACTIVE,
        owner_id=current_user.id,
        created_by=current_user.id,
    )
    db.add(new_org)
    await db.commit()
    await db.refresh(new_org)

    # Invalidate relevant cache entries
    await _invalidate_org_cache(new_org.id)

    return ApiSuccessResponse[OrganizationResponse](
        message="Organization created successfully",
        data=OrganizationResponse.model_validate(new_org)
    )

@router.put("/{org_id}", response_model=ApiSuccessResponse[OrganizationResponse])
@ORGANIZATION_RATE_LIMIT
async def update_organization(
   org_id: HashId,
   request: Request,
   org_data: OrganizationUpdate,
   db: DB 
):
    """
    Update an existing organization.
    """
    query = select(Organization).where(Organization.id == org_id)
    result = await db.execute(query)
    organization = result.scalar_one_or_none()

    if not organization:
        raise NotFoundError(message="Organization not found")

    organization.name = org_data.name
    organization.description = org_data.description
    await db.commit()
    await db.refresh(organization)

    # Invalidate relevant cache entries
    await _invalidate_org_cache(organization.id)

    return ApiSuccessResponse[OrganizationResponse](
        message="Organization updated successfully",
        data=OrganizationResponse.model_validate(organization)
    )

@router.patch("/{org_id}", response_model=ApiSuccessResponse[OrganizationResponse])
@ORGANIZATION_RATE_LIMIT
async def partial_update_organization(
   org_id: HashId,
   request: Request,
   org_data: OrganizationPartialUpdate,
   db: DB
):
   """
   Partially update an existing organization.
   """
   query = select(Organization).where(Organization.id == org_id)
   result = await db.execute(query)
   organization = result.scalar_one_or_none()

   if not organization:
      raise NotFoundError(message="Organization not found")

   organization.status = org_data.status

   await db.commit()
   await db.refresh(organization)

   # Invalidate relevant cache entries
   await _invalidate_org_cache(organization.id)

   return ApiSuccessResponse[OrganizationResponse](
       message="Organization updated successfully",
       data=OrganizationResponse.model_validate(organization)
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
    query = select(Organization).where(Organization.id == org_id)
    result = await db.execute(query)
    organization = result.scalar_one_or_none()

    if not organization:
        raise NotFoundError(message="Organization not found")

    await db.delete(organization)
    await db.commit()

    # Invalidate relevant cache entries
    await _invalidate_org_cache(org_id)

    return ApiSuccessResponse[None](
        message="Organization deleted successfully",
        data=None
    )