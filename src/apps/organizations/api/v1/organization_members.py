from __future__ import annotations

from typing import TYPE_CHECKING
from fastapi import APIRouter, Depends, HTTPException, Query, status
from apps.organizations.schemas.organization_members import OrganizationMemberResponse
from src.core.utils import encode_cursor
from src.apps.organizations.api.v1 import organization
from src.core.exceptions import NotFoundError
from src.apps.organizations.models.organization import Organization
from src.apps.organizations.models.organization_members import OrganizationMember
from src.core.cache import RedisCache
from src.core.dependencies import DB
from src.db.session import get_session
from src.apps.organizations.dependencies import get_current_org
from src.core.types import  HashId
from src.core.schemas import CursorPage, CursorPagination
from src.db.query import select, or_
from src.apps.iam.dependencies import get_current_active_superuser

router = APIRouter(prefix="/organizations/members", tags=["Organization Members"])

@router.get("/", status_code=status.HTTP_200_OK, response_model=CursorPage[OrganizationMemberResponse])
async def list_organization_members(
    pagination: CursorPagination = Depends(),
    org: HashId = Depends(get_current_org),
    search: str | None = Query(
        default=None,
        description="Search term to filter organization members by name or email",
    ),
    db: DB = Depends(get_session),
    current_user=Depends(get_current_active_superuser)
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