from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.organizations.models import OrganizationMember
from src.core.enums import OrganizationMemberStatus
from src.db.query import and_, or_, select


class OrganizationMemberRepository:
    async def get_member(self, db: AsyncSession, org_id: int, user_id: int) -> OrganizationMember | None:
        """Return a membership row for a user in an organization."""
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_member_by_id(self, db: AsyncSession, org_id: int, member_id: int) -> OrganizationMember | None:
        """Return a member record by organization and member id."""
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == member_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, db: AsyncSession, org_id: int):
        """Return a raw select result for all members in an organization."""
        return await db.execute(select(OrganizationMember).where(OrganizationMember.organization_id == org_id))

    async def list_members_paginated(
        self,
        db: AsyncSession,
        org_id: int,
        search: str | None = None,
        member_status=None,
        query_filter_fn=None,
        query_order_fn=None,
        limit: int = 50,
    ) -> Sequence[OrganizationMember]:
        """List organization members with optional search, status and pagination."""
        query = select(OrganizationMember).where(OrganizationMember.organization_id == org_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    OrganizationMember.user.username.ilike(search_term),
                    OrganizationMember.user.email.ilike(search_term),
                )
            )
        if member_status is not None:
            query = query.where(OrganizationMember.status == member_status)

        if query_filter_fn:
            query = query_filter_fn(query)
        if query_order_fn:
            query = query_order_fn(query)

        query = query.limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create_member(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        organization_id: int,
        status: OrganizationMemberStatus,
        invited_by: int | None = None,
        role: str | None = None,
        joined_at: datetime | None = None,
    ) -> OrganizationMember:
        """Create a membership entity without committing."""
        member = OrganizationMember(
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            invited_by=invited_by,
            role=role,
            joined_at=joined_at,
        )
        db.add(member)
        return member

    async def create_member_and_commit(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        organization_id: int,
        status: OrganizationMemberStatus,
        invited_by: int | None = None,
        role: str | None = None,
        joined_at: datetime | None = None,
        refresh: bool = False,
    ) -> OrganizationMember:
        """Create and commit a membership row, optionally refreshing the entity."""
        member = await self.create_member(
            db,
            user_id=user_id,
            organization_id=organization_id,
            status=status,
            invited_by=invited_by,
            role=role,
            joined_at=joined_at,
        )
        await db.commit()
        if refresh:
            await db.refresh(member)
        return member

    async def get_invited_member(self, db: AsyncSession, *, org_id: int, user_id: int) -> OrganizationMember | None:
        """Return an invited membership for a user in an organization."""
        result = await db.execute(
            select(OrganizationMember).where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.status == OrganizationMemberStatus.INVITED,
                )
            )
        )
        return result.scalar_one_or_none()

    async def accept_member_invitation_and_commit(
        self,
        db: AsyncSession,
        *,
        member: OrganizationMember,
        token_jti: str | None,
        user_id: int,
    ) -> None:
        """Activate an invited member and optionally persist used-invitation token."""
        member.status = OrganizationMemberStatus.ACTIVE
        if token_jti:
            from src.apps.iam.models.used_token import UsedToken

            db.add(
                UsedToken(
                    token_jti=token_jti,
                    user_id=user_id,
                    token_purpose="organization_invitation",
                )
            )
        await db.commit()

    async def delete_member_and_commit(self, db: AsyncSession, member: OrganizationMember) -> None:
        """Delete a membership row and commit."""
        await db.delete(member)
        await db.commit()

    async def list_members_by_org_and_users(self, db: AsyncSession, org_id: int, user_ids: list[int]):
        """Return members in an organization filtered by a list of user ids."""
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id.in_(user_ids),
            )
        )
        return result.scalars().all()
