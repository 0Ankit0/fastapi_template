from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.organizations.models import Organization
from src.core.enums import OrganizationStatus
from src.db.query import or_, select


class OrganizationModelRepository:
    async def list_organizations(self, db: AsyncSession):
        """Return a raw select result for all organizations."""
        return await db.execute(select(Organization))

    async def list_organizations_paginated(
        self,
        db: AsyncSession,
        search: str | None = None,
        org_status=None,
        owner_id: int | None = None,
        query_filter_fn=None,
        query_order_fn=None,
        limit: int = 50,
    ) -> Sequence[Organization]:
        """List organizations with optional search, owner, status and cursor filters."""
        query = select(Organization)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Organization.name.ilike(search_term),
                    Organization.description.ilike(search_term),
                )
            )
        if org_status is not None:
            query = query.where(Organization.status == org_status)
        if owner_id is not None:
            query = query.where(Organization.owner_id == owner_id)

        if query_filter_fn:
            query = query_filter_fn(query)
        if query_order_fn:
            query = query_order_fn(query)

        query = query.limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, org_id: int) -> Organization | None:
        """Return an organization by id, or None if missing."""
        result = await db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def get_by_slug(self, db: AsyncSession, slug: str) -> Organization | None:
        """Return an organization by slug, or None if missing."""
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, name: str, description: str | None, owner_id: int, created_by: int) -> Organization:
        """Create an organization entity without committing."""
        organization = Organization(
            name=name,
            slug=name,
            description=description,
            status=OrganizationStatus.ACTIVE,
            owner_id=owner_id,
            created_by=created_by,
        )
        db.add(organization)
        return organization

    async def delete(self, db: AsyncSession, organization: Organization) -> None:
        """Mark an organization for deletion in the current transaction."""
        await db.delete(organization)

    async def commit(self, db: AsyncSession) -> None:
        """Commit the active organization transaction."""
        await db.commit()

    async def refresh(self, db: AsyncSession, instance: Any) -> None:
        """Refresh an ORM entity from the database."""
        await db.refresh(instance)

    async def create_organization_and_commit(
        self,
        db: AsyncSession,
        *,
        name: str,
        description: str | None,
        owner_id: int,
        created_by: int,
        slug: str,
    ) -> Organization:
        """Create an organization, set slug, commit, and return refreshed entity."""
        organization = await self.create(
            db,
            name=name,
            description=description,
            owner_id=owner_id,
            created_by=created_by,
        )
        organization.slug = slug
        await db.commit()
        await db.refresh(organization)
        return organization

    async def update_organization_and_commit(
        self,
        db: AsyncSession,
        *,
        organization: Organization,
        name: str | None = None,
        description: str | None = None,
        status: OrganizationStatus | None = None,
    ) -> Organization:
        """Apply mutable organization fields, commit, and return refreshed entity."""
        if name is not None:
            organization.name = name
        if description is not None:
            organization.description = description
        if status is not None:
            organization.status = status

        await db.commit()
        await db.refresh(organization)
        return organization

    async def delete_and_commit(self, db: AsyncSession, organization: Organization) -> None:
        """Delete an organization and commit the transaction."""
        await db.delete(organization)
        await db.commit()
