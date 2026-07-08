from __future__ import annotations

from datetime import datetime, timezone

import src.core.security as security
from src.apps.iam.repositories import iam_repository
from src.apps.iam.services.policy_service import PolicyService
from src.apps.organizations.models import OrganizationMember
from src.apps.organizations.repositories import organization_repository
from src.apps.organizations.schemas.organization_members import (
    OrganizationMemberResponse,
    OrganizationMembershipInvitationRequest,
)
from src.core.cache import RedisCache
from src.core.enums import OrganizationMemberStatus
from src.core.exceptions import NotFoundError, ValidationError
from src.core.pagination import (
    CursorSortDirection,
    apply_id_cursor_filter,
    apply_id_ordering,
    build_id_cursor,
    to_cursor_page,
)
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination


class OrganizationMembersService:
    async def invalidate_org_members_cache(self, org_id: int) -> None:
        """Clear cached organization-member list/detail entries."""
        await RedisCache.clear_pattern(f"org:{org_id}:members:*")
        await RedisCache.clear_pattern(f"org:{org_id}:member:*")

    async def list_organization_members(
        self,
        db,
        *,
        org,
        pagination: CursorPagination,
        search: str | None,
        member_status,
        sort_direction: CursorSortDirection,
    ) -> CursorPage[OrganizationMemberResponse]:
        """Return paginated members for an organization with role metadata."""
        cache_key = (
            f"org:{org.id}:members:{pagination.cursor}:{pagination.limit}:"
            f"{search}:{member_status}:{sort_direction.value}"
        )
        cached_result = await RedisCache.get(cache_key)
        if cached_result:
            return CursorPage[OrganizationMemberResponse].model_validate_json(cached_result)

        def apply_filter(q):
            """Apply cursor filtering to organization-member query."""
            return apply_id_cursor_filter(
                q,
                pagination,
                id_column=OrganizationMember.id,
                direction=sort_direction,
            )
        
        def apply_order(q):
            """Apply stable id ordering for member pagination."""
            return apply_id_ordering(
                q,
                id_column=OrganizationMember.id,
                direction=sort_direction,
            )

        members = await organization_repository.list_members_paginated(
            db,
            org.id,
            search=search,
            member_status=member_status,
            query_filter_fn=apply_filter,
            query_order_fn=apply_order,
            limit=pagination.limit + 1,
        )
        role_map = PolicyService.get_org_members_map(org.slug)

        response = to_cursor_page(
            members,
            pagination,
            serializer=lambda member: OrganizationMemberResponse(
                **OrganizationMemberResponse.model_validate(member).model_dump(exclude={"role"}),
                role=role_map.get(member.user_id, []),
            ),
            next_cursor_builder=build_id_cursor,
        )
        await RedisCache.set(cache_key, response.model_dump_json(), ttl=120)
        return response

    async def get_organization_member(self, db, *, org, member_id: int) -> ApiSuccessResponse[OrganizationMemberResponse]:
        """Return one organization member with resolved role assignments."""
        cache_key = f"org:{org.id}:member:{member_id}"
        cached_result = await RedisCache.get(cache_key)
        if cached_result:
            return ApiSuccessResponse[OrganizationMemberResponse](
                message="Organization member retrieved successfully",
                data=OrganizationMemberResponse.model_validate_json(cached_result),
            )

        member = await organization_repository.get_member(db, org.id, member_id)
        if not member:
            raise NotFoundError(message="Organization member not found for org")

        response = OrganizationMemberResponse(
            **OrganizationMemberResponse.model_validate(member).model_dump(exclude={"role"})
        )
        response.role = PolicyService.get_org_members_map(org.slug).get(member_id, [])
        await RedisCache.set(cache_key, response.model_dump_json(), ttl=120)
        return ApiSuccessResponse[OrganizationMemberResponse](
            message="Organization member retrieved successfully",
            data=response,
        )

    async def add_member(self, db, *, member_id: int, current_user, org, request) -> ApiSuccessResponse[None]:
        """Invite an existing user to join the organization."""
        member = await organization_repository.get_member(db, org.id, member_id)
        if member:
            raise ValidationError(message="User is already a member of the organization")

        user = await organization_repository.get_user_by_id(db, member_id)
        if not user:
            raise NotFoundError(message="User not found")

        organization_member = await organization_repository.create_member(
            db,
            user_id=member_id,
            organization_id=org.id,
            status=OrganizationMemberStatus.INVITED,
            invited_by=current_user.id,
            joined_at=datetime.now(timezone.utc),
        )
        await organization_repository.commit(db)
        await organization_repository.refresh(db, organization_member)

        from src.apps.organizations.services.email import OrganizationEmailService

        invitation_token = security.create_organization_invitation_token(subject=member_id, Organization=str(org.id))
        await OrganizationEmailService.send_member_invitation_email(
            user=user,
            url=request.url_for("accept_invitation"),
            email=user.email,
            token=invitation_token,
            org_slug=org.slug,
        )

        await organization_repository.create_invitation_tracking_and_commit(
            db,
            user_id=user.id,
            request_user_agent=request.headers.get("user-agent") or "",
            ip_address=request.client.host if request.client else None,
        )
        await self.invalidate_org_members_cache(org.id)
        return ApiSuccessResponse[None](message="Organization member invited successfully", data=None)

    async def invite_member(self, db, *, data: OrganizationMembershipInvitationRequest, org, request) -> ApiSuccessResponse[None]:
        """Invite by email, creating immediate membership for existing users."""
        user = await organization_repository.get_user_by_email(db, data.email)
        if user:
            existing_member = await organization_repository.get_member(db, org.id, user.id)
            if existing_member:
                raise ValidationError(message="User is already a member of the organization")
            await organization_repository.create_member_and_commit(
                db,
                user_id=user.id,
                organization_id=org.id,
                role=data.role,
                status=OrganizationMemberStatus.ACTIVE,
            )

        from src.apps.organizations.services.email import OrganizationEmailService

        invitation_token = security.create_organization_invitation_token(subject=data.email, Organization=str(org.id))
        await OrganizationEmailService.send_member_invitation_email(
            user=None,
            url=request.url_for("accept_invitation"),
            email=data.email,
            token=invitation_token,
            org_slug=org.slug,
        )

        await organization_repository.create_invitation_tracking_and_commit(
            db,
            user_id=None,
            request_user_agent=request.headers.get("user-agent") or "",
            ip_address=request.client.host if request.client else None,
        )
        await self.invalidate_org_members_cache(org.id)
        return ApiSuccessResponse[None](message="Organization member invited successfully", data=None)

    async def resend_invite(self, db, *, member_id: int, org, request) -> ApiSuccessResponse[OrganizationMemberResponse]:
        """Resend invitation email for members still in invited status."""
        member = await organization_repository.get_member(db, org.id, member_id)
        if not member:
            raise NotFoundError(message="Organization member not found")
        if member.status != OrganizationMemberStatus.INVITED:
            raise ValidationError(message="Only invited members can be resent an invitation")

        from src.apps.organizations.services.email import OrganizationEmailService

        invitation_token = security.create_organization_invitation_token(
            subject=member.user.id,
            Organization=str(member.organization_id),
        )
        await OrganizationEmailService.send_member_invitation_email(
            user=member.user,
            url=request.url_for("accept_invitation"),
            email=None,
            token=invitation_token,
            org_slug=member.organization.slug,
        )
        await organization_repository.create_invitation_tracking_and_commit(
            db,
            user_id=member.user.id,
            request_user_agent=request.headers.get("user-agent") or "",
            ip_address=request.client.host if request.client else None,
        )

        return ApiSuccessResponse[OrganizationMemberResponse](
            message="Invitation resent successfully",
            data=OrganizationMemberResponse.model_validate(member),
        )

    async def remove_member(self, db, *, member_id: int, org) -> ApiSuccessResponse[None]:
        """Remove a member from an organization and revoke policy bindings."""
        member = await organization_repository.get_member(db, org.id, member_id)
        if not member:
            raise NotFoundError(message="Organization member not found")

        PolicyService.remove_user_from_org(user_id=member_id, org_slug=org.slug)
        await organization_repository.delete_member_and_commit(db, member)
        await self.invalidate_org_members_cache(org.id)
        return ApiSuccessResponse[None](message="Organization member removed successfully", data=None)

    async def accept_invitation(self, db, *, token: str) -> ApiSuccessResponse[None]:
        """Accept an invitation token and activate the invited membership."""
        try:
            token_data = security.verify_secure_url_token(token)
        except Exception:
            raise ValidationError("Invalid or expired accept invitation token.")

        user_id = token_data.get("user_id")
        org_slug = token_data.get("org_slug")
        paseto_token = token_data.get("token")
        purpose = token_data.get("purpose")

        if not all([user_id, org_slug, paseto_token]) or purpose != "organization_invitation":
            raise ValidationError("Invalid invitation token data")

        payload = security.verify_token(paseto_token, token_type=security.TokenType.ORGANIZATION_INVITATION)
        token_jti = payload.get("jti")

        if str(payload.get("sub")) != str(user_id):
            raise ValidationError("Token data mismatch - possible tampering detected")

        if token_jti and await iam_repository.get_used_token_by_jti(db, token_jti):
            raise ValidationError("This organization invitation link has already been used")

        org = await organization_repository.get_by_slug(db, str(org_slug))
        if not org:
            raise NotFoundError("Organization not found for this invitation token")

        member = await organization_repository.get_invited_member(
            db,
            org_id=org.id,
            user_id=int(user_id),
        )
        if not member:
            raise ValidationError("User not found for this invitation token")

        await organization_repository.accept_member_invitation_and_commit(
            db,
            member=member,
            token_jti=token_jti,
            user_id=int(user_id),
        )
        await self.invalidate_org_members_cache(member.organization_id)
        return ApiSuccessResponse[None](message="Organization invitation accepted successfully")


organization_members_service = OrganizationMembersService()
