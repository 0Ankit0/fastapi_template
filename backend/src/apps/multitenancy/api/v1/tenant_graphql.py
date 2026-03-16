import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from graphql import GraphQLError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, col

from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.casbin_enforcer import CasbinEnforcer
from src.apps.multitenancy.models.tenant import (
    InvitationStatus,
    Tenant,
    TenantInvitation,
    TenantMember,
    TenantRole,
)
from src.apps.iam.models.user import User
from src.apps.multitenancy.schemas.tenant import (
    TenantCreate,
    TenantInvitationResponse,
    TenantMemberResponse,
    TenantResponse,
    TenantWithMembersResponse,
)
from src.apps.multitenancy.schemas.graphql_tenant import (
    TenantInvitationType,
    TenantMemberType,
    TenantType,
    TenantWithMembersType,
)
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.core.cache import RedisCache
from src.apps.core.schemas import PaginatedResponse
from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import TenantEvents


_INVITATION_TTL_HOURS = 48


async def _get_tenant_or_404(tenant_id: int, db: AsyncSession) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise GraphQLError("Tenant not found")
    return tenant


async def _require_tenant_role(
    tenant_id: int,
    user: User,
    db: AsyncSession,
    min_role: TenantRole = TenantRole.ADMIN,
) -> TenantMember:
    membership = (
        await db.execute(
            select(TenantMember).where(
                TenantMember.tenant_id == tenant_id,
                TenantMember.user_id == user.id,
                TenantMember.is_active == True,
            )
        )
    ).scalars().first()

    if not membership:
        raise GraphQLError("Not a member of this tenant")

    role_order = {TenantRole.MEMBER: 0, TenantRole.ADMIN: 1, TenantRole.OWNER: 2}
    if role_order[membership.role] < role_order[min_role]:
        raise GraphQLError("Insufficient permissions in tenant")

    return membership


@strawberry.type
class PaginatedTenants:
    items: List[TenantWithMembersType]
    total: int
    skip: int
    limit: int
    has_more: bool


@strawberry.type
class PaginatedTenantMembers:
    items: List[TenantMemberType]
    total: int
    skip: int
    limit: int
    has_more: bool


@strawberry.type
class PaginatedTenantInvitations:
    items: List[TenantInvitationType]
    total: int
    skip: int
    limit: int
    has_more: bool


async def get_graphql_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> dict:
    """Expose FastAPI dependencies to Strawberry resolvers."""
    return {"current_user": current_user, "db": db, "analytics": analytics}


@strawberry.type
class Query:
    @strawberry.field
    async def my_tenants(self, info: Info, skip: int = 0, limit: int = 10) -> PaginatedTenants:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        cache_key = f"tenants:list:{current_user.id}:{skip}:{limit}"
        cached = await RedisCache.get(cache_key)
        if cached:
            return PaginatedTenants(**cached)

        total = (
            await db.execute(
                select(func.count(col(Tenant.id)))
                .join(TenantMember, col(TenantMember.tenant_id) == Tenant.id)
                .where(col(TenantMember.user_id) == current_user.id, col(TenantMember.is_active) == True)
            )
        ).scalar_one()

        items = (
            await db.execute(
                select(Tenant)
                .join(TenantMember, col(TenantMember.tenant_id) == Tenant.id)
                .where(col(TenantMember.user_id) == current_user.id, col(TenantMember.is_active) == True)
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        items_resp = [
            TenantWithMembersType.from_pydantic(
                TenantWithMembersResponse.model_validate(t)
            )
            for t in items
        ]

        payload = {
            "items": [t.__dict__ for t in items_resp],
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + len(items_resp)) < total,
        }
        await RedisCache.set(cache_key, payload, ttl=120)
        return PaginatedTenants(**payload)

    @strawberry.field
    async def tenant(self, info: Info, tenant_id: str) -> TenantWithMembersType:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        uid = decode_id_or_404(tenant_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.MEMBER)
        tenant = await _get_tenant_or_404(uid, db)

        members_raw = (
            await db.execute(
                select(TenantMember).where(TenantMember.tenant_id == uid)
            )
        ).scalars().all()

        return TenantWithMembersType.from_pydantic(
            TenantWithMembersResponse(
                **TenantResponse.model_validate(tenant).model_dump(),
                members=[
                    # type: ignore
                    m  # TenantMemberResponse already serializes IDs
                    for m in [
                        TenantMemberResponse.model_validate(x) for x in members_raw
                    ]
                ],
            )
        )

    @strawberry.field
    async def tenant_members(
        self,
        info: Info,
        tenant_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> PaginatedTenantMembers:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        uid = decode_id_or_404(tenant_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.MEMBER)

        total = (
            await db.execute(
                select(func.count(col(TenantMember.id))).where(TenantMember.tenant_id == uid)
            )
        ).scalar_one()

        items = (
            await db.execute(
                select(TenantMember)
                .where(TenantMember.tenant_id == uid)
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        items_resp = [TenantMemberType.from_pydantic(TenantMemberResponse.model_validate(m)) for m in items]
        return PaginatedTenantMembers(
            items=items_resp,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + len(items_resp)) < total,
        )

    @strawberry.field
    async def tenant_invitations(
        self,
        info: Info,
        tenant_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> PaginatedTenantInvitations:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        uid = decode_id_or_404(tenant_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.ADMIN)

        total = (
            await db.execute(
                select(func.count(col(TenantInvitation.id))).where(TenantInvitation.tenant_id == uid)
            )
        ).scalar_one()

        items = (
            await db.execute(
                select(TenantInvitation)
                .where(TenantInvitation.tenant_id == uid)
                .offset(skip)
                .limit(limit)
            )
        ).scalars().all()

        items_resp = [
            TenantInvitationType.from_pydantic(TenantInvitationResponse.model_validate(i))
            for i in items
        ]
        return PaginatedTenantInvitations(
            items=items_resp,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + len(items_resp)) < total,
        )


@strawberry.input
class TenantCreateInput:
    """GraphQL input for creating a tenant."""

    name: str
    slug: str
    description: Optional[str] = ""


@strawberry.input
class TenantUpdateInput:
    """GraphQL input for updating a tenant."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.input
class TenantMemberUpdateInput:
    """GraphQL input for updating a tenant member."""

    role: TenantRole


@strawberry.input
class TenantInvitationCreateInput:
    """GraphQL input for creating a tenant invitation."""

    email: str
    role: TenantRole = TenantRole.MEMBER


@strawberry.input
class AcceptInvitationInput:
    """GraphQL input for accepting an invitation."""

    token: str


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_tenant(self, info: Info, data: TenantCreateInput) -> TenantType:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]
        analytics: AnalyticsService = ctx["analytics"]

        validated = TenantCreate.model_validate(data.__dict__)

        existing = (
            await db.execute(select(Tenant).where(Tenant.slug == validated.slug))
        ).scalars().first()
        if existing:
            raise GraphQLError("Slug already taken")

        tenant = Tenant(
            name=validated.name,
            slug=validated.slug,
            description=validated.description,
            owner_id=current_user.id,
        )
        db.add(tenant)
        await db.flush()

        membership = TenantMember(
            tenant_id=tenant.id,
            user_id=current_user.id,
            role=TenantRole.OWNER,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(tenant)

        await CasbinEnforcer.add_role_for_user(str(current_user.id), TenantRole.OWNER, tenant.slug)

        await RedisCache.clear_pattern(f"tenants:list:*")
        await analytics.capture(
            str(current_user.id),
            TenantEvents.TENANT_CREATED,
            {"tenant_id": tenant.id, "tenant_slug": tenant.slug, "tenant_name": tenant.name},
        )

        return TenantType.from_pydantic(TenantResponse.model_validate(tenant))

    @strawberry.mutation
    async def update_tenant(self, info: Info, tenant_id: str, data: TenantUpdateInput) -> TenantType:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        uid = decode_id_or_404(tenant_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.ADMIN)
        tenant = await _get_tenant_or_404(uid, db)

        update_fields = {k: v for k, v in data.__dict__.items() if v is not None}
        for field, value in update_fields.items():
            setattr(tenant, field, value)
        tenant.updated_at = datetime.now()

        await db.commit()
        await db.refresh(tenant)

        await RedisCache.clear_pattern(f"tenants:list:*")
        return TenantType.from_pydantic(TenantResponse.model_validate(tenant))

    @strawberry.mutation
    async def delete_tenant(self, info: Info, tenant_id: str) -> bool:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        uid = decode_id_or_404(tenant_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.OWNER)
        tenant = await _get_tenant_or_404(uid, db)
        await db.delete(tenant)
        await db.commit()
        await RedisCache.clear_pattern(f"tenants:list:*")
        return True

    @strawberry.mutation
    async def update_member_role(
        self,
        info: Info,
        tenant_id: str,
        user_id: str,
        data: TenantMemberUpdateInput,
    ) -> TenantMemberType:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        uid = decode_id_or_404(tenant_id)
        uid_user = decode_id_or_404(user_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.ADMIN)

        if data.role == TenantRole.OWNER:
            await _require_tenant_role(uid, current_user, db, min_role=TenantRole.OWNER)

        membership = (
            await db.execute(
                select(TenantMember).where(
                    TenantMember.tenant_id == uid,
                    TenantMember.user_id == uid_user,
                )
            )
        ).scalars().first()

        if not membership:
            raise GraphQLError("Member not found")

        tenant = await _get_tenant_or_404(uid, db)

        await CasbinEnforcer.remove_role_for_user(str(uid_user), membership.role, tenant.slug)
        membership.role = data.role
        await CasbinEnforcer.add_role_for_user(str(uid_user), data.role, tenant.slug)

        await db.commit()
        await db.refresh(membership)
        return TenantMemberType.from_pydantic(TenantMemberResponse.model_validate(membership))

    @strawberry.mutation
    async def remove_member(self, info: Info, tenant_id: str, user_id: str) -> bool:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]
        analytics: AnalyticsService = ctx["analytics"]

        uid = decode_id_or_404(tenant_id)
        uid_user = decode_id_or_404(user_id)
        if uid_user != current_user.id:
            await _require_tenant_role(uid, current_user, db, min_role=TenantRole.ADMIN)

        membership = (
            await db.execute(
                select(TenantMember).where(
                    TenantMember.tenant_id == uid,
                    TenantMember.user_id == uid_user,
                )
            )
        ).scalars().first()
        if not membership:
            raise GraphQLError("Member not found")

        tenant = await _get_tenant_or_404(uid, db)

        if membership.role == TenantRole.OWNER:
            owners_count = (
                await db.execute(
                    select(func.count(col(TenantMember.id))).where(
                        TenantMember.tenant_id == uid,
                        TenantMember.role == TenantRole.OWNER,
                    )
                )
            ).scalar_one()
            if owners_count <= 1:
                raise GraphQLError(
                    "Cannot remove the last owner. Transfer ownership first."
                )

        await CasbinEnforcer.remove_role_for_user(str(uid_user), membership.role, tenant.slug)
        await db.delete(membership)
        await db.commit()

        await analytics.capture(
            str(current_user.id),
            TenantEvents.TENANT_MEMBER_REMOVED,
            {"tenant_id": uid, "removed_user_id": uid_user},
        )

        return True

    @strawberry.mutation
    async def invite_member(
        self,
        info: Info,
        tenant_id: str,
        data: TenantInvitationCreateInput,
    ) -> TenantInvitationType:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]
        analytics: AnalyticsService = ctx["analytics"]

        uid = decode_id_or_404(tenant_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.ADMIN)
        await _get_tenant_or_404(uid, db)

        existing = (
            await db.execute(
                select(TenantInvitation).where(
                    TenantInvitation.tenant_id == uid,
                    TenantInvitation.email == data.email,
                    TenantInvitation.status == InvitationStatus.PENDING,
                )
            )
        ).scalars().first()
        if existing:
            raise GraphQLError(
                "An active invitation already exists for this email",
            )

        invitation = TenantInvitation(
            tenant_id=uid,
            email=str(data.email),
            role=data.role,
            invited_by=current_user.id,
            token=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(hours=_INVITATION_TTL_HOURS),
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)

        await analytics.capture(
            str(current_user.id),
            TenantEvents.TENANT_MEMBER_INVITED,
            {"tenant_id": uid, "invitee_email": str(data.email), "role": data.role.value},
        )
        return TenantInvitationType.from_pydantic(TenantInvitationResponse.model_validate(invitation))

    @strawberry.mutation
    async def accept_invitation(self, info: Info, data: AcceptInvitationInput) -> TenantMemberType:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]
        analytics: AnalyticsService = ctx["analytics"]

        invitation = (
            await db.execute(
                select(TenantInvitation).where(TenantInvitation.token == data.token)
            )
        ).scalars().first()

        if not invitation:
            raise GraphQLError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING:
            raise GraphQLError(f"Invitation is {invitation.status}")

        if invitation.expires_at < datetime.now():
            invitation.status = InvitationStatus.EXPIRED
            await db.commit()
            raise GraphQLError("Invitation has expired")

        if invitation.email != current_user.email:
            raise GraphQLError(
                "This invitation was sent to a different email address",
            )

        already = (
            await db.execute(
                select(TenantMember).where(
                    TenantMember.tenant_id == invitation.tenant_id,
                    TenantMember.user_id == current_user.id,
                )
            )
        ).scalars().first()
        if already:
            raise GraphQLError("Already a member of this tenant")

        tenant = await _get_tenant_or_404(invitation.tenant_id, db)

        membership = TenantMember(
            tenant_id=invitation.tenant_id,
            user_id=current_user.id,
            role=invitation.role,
        )
        db.add(membership)

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now()
        await db.commit()
        await db.refresh(membership)

        await CasbinEnforcer.add_role_for_user(str(current_user.id), invitation.role, tenant.slug)
        await RedisCache.clear_pattern(f"tenants:list:*")
        await analytics.capture(
            str(current_user.id),
            TenantEvents.TENANT_MEMBER_JOINED,
            {"tenant_id": tenant.id, "tenant_slug": tenant.slug, "role": invitation.role.value},
        )
        return TenantMemberType.from_pydantic(TenantMemberResponse.model_validate(membership))

    @strawberry.mutation
    async def revoke_invitation(self, info: Info, tenant_id: str, invitation_id: str) -> bool:
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        uid = decode_id_or_404(tenant_id)
        iid = decode_id_or_404(invitation_id)
        await _require_tenant_role(uid, current_user, db, min_role=TenantRole.ADMIN)

        invitation = (
            await db.execute(
                select(TenantInvitation).where(
                    TenantInvitation.id == iid,
                    TenantInvitation.tenant_id == uid,
                )
            )
        ).scalars().first()
        if not invitation:
            raise GraphQLError("Invitation not found")

        if invitation.status != InvitationStatus.PENDING:
            raise GraphQLError(
                "Only pending invitations can be revoked",
            )

        invitation.status = InvitationStatus.REVOKED
        await db.commit()
        return True


schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_router = GraphQLRouter(schema, context_getter=get_graphql_context)
