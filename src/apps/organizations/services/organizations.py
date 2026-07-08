from __future__ import annotations

from slugify import slugify

from src.apps.organizations.models.organization import Organization
from src.apps.organizations.repositories import organization_repository
from src.apps.organizations.schemas.organization import (
    OrganizationCreate,
    OrganizationPartialUpdate,
    OrganizationResponse,
    OrganizationUpdate,
)
from src.core.cache import RedisCache
from src.core.exceptions import NotFoundError
from src.core.pagination import (
    CursorSortDirection,
    apply_id_cursor_filter,
    apply_id_ordering,
    build_id_cursor,
    to_cursor_page,
)
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination


class OrganizationService:
    async def invalidate_org_cache(self, org_id: int) -> None:
        """Clear organization detail and derived cache keys."""
        await RedisCache.delete(f"org:{org_id}")
        await RedisCache.clear_pattern(f"org:{org_id}:*")

    async def list_organizations(
        self,
        db,
        *,
        pagination: CursorPagination,
        search: str | None,
        org_status,
        owner_id,
        sort_direction: CursorSortDirection,
    ) -> CursorPage[OrganizationResponse]:
        """Return paginated organizations with optional filter criteria."""
        cache_key = (
            f"org:list:{pagination.cursor}:{pagination.limit}:"
            f"{search}:{org_status}:{owner_id}:{sort_direction.value}"
        )
        cached_result = await RedisCache.get(cache_key)
        if cached_result:
            return CursorPage[OrganizationResponse].model_validate_json(cached_result)

        def apply_filter(q):
            """Apply cursor filtering to organization query."""
            return apply_id_cursor_filter(
                q,
                pagination,
                id_column=Organization.id,
                direction=sort_direction,
            )
        
        def apply_order(q):
            """Apply stable id ordering for organization pagination."""
            return apply_id_ordering(
                q,
                id_column=Organization.id,
                direction=sort_direction,
            )

        organizations = await organization_repository.list_organizations_paginated(
            db,
            search=search,
            org_status=org_status,
            owner_id=owner_id,
            query_filter_fn=apply_filter,
            query_order_fn=apply_order,
            limit=pagination.limit + 1,
        )
        response = to_cursor_page(
            organizations,
            pagination,
            serializer=OrganizationResponse.model_validate,
            next_cursor_builder=build_id_cursor,
        )
        await RedisCache.set(cache_key, response.model_dump_json(), ttl=120)
        return response

    async def get_organization(self, db, *, org_id: int) -> ApiSuccessResponse[OrganizationResponse]:
        """Return a single organization by id, using cache when possible."""
        cache_key = f"org:{org_id}"
        cached_org = await RedisCache.get(cache_key)
        if cached_org:
            return ApiSuccessResponse[OrganizationResponse](
                message="Organization retrieved successfully",
                data=OrganizationResponse.model_validate_json(cached_org),
            )

        organization = await organization_repository.get_by_id(db, org_id)
        if not organization:
            raise NotFoundError(message="Organization not found")

        response = OrganizationResponse.model_validate(organization)
        await RedisCache.set(cache_key, response.model_dump_json(), ttl=300)
        return ApiSuccessResponse[OrganizationResponse](
            message="Organization retrieved successfully",
            data=response,
        )

    async def create_organization(self, db, *, org_data: OrganizationCreate, current_user_id: int) -> ApiSuccessResponse[OrganizationResponse]:
        """Create a new organization for the current user."""
        new_org = await organization_repository.create_organization_and_commit(
            db,
            name=org_data.name,
            description=org_data.description,
            owner_id=current_user_id,
            created_by=current_user_id,
            slug=slugify(org_data.name),
        )
        await self.invalidate_org_cache(new_org.id)
        return ApiSuccessResponse[OrganizationResponse](
            message="Organization created successfully",
            data=OrganizationResponse.model_validate(new_org),
        )

    async def update_organization(self, db, *, org_id: int, org_data: OrganizationUpdate) -> ApiSuccessResponse[OrganizationResponse]:
        """Update core organization fields by id."""
        organization = await organization_repository.get_by_id(db, org_id)
        if not organization:
            raise NotFoundError(message="Organization not found")

        organization = await organization_repository.update_organization_and_commit(
            db,
            organization=organization,
            name=org_data.name,
            description=org_data.description,
        )
        await self.invalidate_org_cache(organization.id)
        return ApiSuccessResponse[OrganizationResponse](
            message="Organization updated successfully",
            data=OrganizationResponse.model_validate(organization),
        )

    async def partial_update_organization(
        self,
        db,
        *,
        org_id: int,
        org_data: OrganizationPartialUpdate,
    ) -> ApiSuccessResponse[OrganizationResponse]:
        """Partially update mutable organization state fields."""
        organization = await organization_repository.get_by_id(db, org_id)
        if not organization:
            raise NotFoundError(message="Organization not found")

        organization = await organization_repository.update_organization_and_commit(
            db,
            organization=organization,
            status=org_data.status,
        )
        await self.invalidate_org_cache(organization.id)
        return ApiSuccessResponse[OrganizationResponse](
            message="Organization updated successfully",
            data=OrganizationResponse.model_validate(organization),
        )

    async def delete_organization(self, db, *, org_id: int) -> ApiSuccessResponse[None]:
        """Delete an organization by id and invalidate caches."""
        organization = await organization_repository.get_by_id(db, org_id)
        if not organization:
            raise NotFoundError(message="Organization not found")

        await organization_repository.delete_and_commit(db, organization)
        await self.invalidate_org_cache(org_id)
        return ApiSuccessResponse[None](message="Organization deleted successfully", data=None)


organization_service = OrganizationService()
