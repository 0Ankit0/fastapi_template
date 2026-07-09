"""User application service for IAM user endpoints."""

from __future__ import annotations

import uuid
from typing import Iterable

from fastapi import HTTPException, UploadFile, status

from src.apps.iam.models.user import User
from src.apps.iam.repositories import iam_repository
from src.apps.iam.schemas.user import UserResponse, UserUpdate
from src.apps.iam.services.policy_service import PolicyService
from src.core.cache import RedisCache
from src.core.config import settings
from src.core.enums import UserStatus
from src.core.pagination import CursorSortDirection, apply_id_cursor_filter, apply_id_ordering, build_id_cursor, to_cursor_page
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination
from src.core.storage import delete_media, save_media_bytes
from src.core.types import HashId


class UserService:
    @staticmethod
    def _serialize_user_response(user: User, roles: Iterable) -> UserResponse:
        """Map user and role data into the API response schema."""
        return UserResponse.model_validate(
            {
                "id": user.id,
                "username": user.username,
                "email": str(user.email),
                "is_active": user.status == UserStatus.ACTIVE,
                "is_superuser": user.is_superuser,
                "is_confirmed": user.is_confirmed,
                "otp_enabled": user.otp_enabled,
                "otp_verified": user.otp_verified,
                "first_name": user.profile.first_name if user.profile else None,
                "last_name": user.profile.last_name if user.profile else None,
                "phone": user.profile.phone if user.profile else None,
                "image_url": user.profile.avatar_url if user.profile else None,
                "bio": user.profile.bio if user.profile else None,
                "roles": list(roles),
            }
        )

    @staticmethod
    async def invalidate_user_cache(user_id: int) -> None:
        """Clear cached profile and derived cache entries for a user."""
        await RedisCache.delete(f"user:profile:{user_id}")
        await RedisCache.clear_pattern(f"user:{user_id}:*")

    @staticmethod
    async def invalidate_user_listing_cache() -> None:
        """Clear cached paginated user list responses."""
        await RedisCache.clear_pattern("users:list:*")

    async def get_current_user_profile(self, current_user: User, org_slug: str | None) -> UserResponse:
        """Return the current user profile, preferring cached representation."""
        cache_key = f"user:profile:{current_user.id}"

        cached = await RedisCache.get(cache_key)
        if cached:
            return UserResponse.model_validate(cached)

        roles = PolicyService.get_user_org_roles(current_user.id, org_slug or "global")
        response = self._serialize_user_response(current_user, roles)
        await RedisCache.set(cache_key, response.model_dump(mode="json"), ttl=300)
        return response

    async def list_users(
        self,
        db,
        *,
        org_slug: str,
        pagination: CursorPagination,
        search: str | None,
        is_active: bool | None,
        sort_direction: CursorSortDirection,
    ) -> CursorPage[UserResponse]:
        """Return a cursor-paginated user list enriched with organization roles."""
        cache_key = (
            f"users:list:{org_slug}:"
            f"{pagination.cursor}:"
            f"{pagination.limit}:"
            f"{search}:"
            f"{is_active}:{sort_direction.value}"
        )

        cached = await RedisCache.get(cache_key)
        if cached:
            return CursorPage[UserResponse].model_validate(cached)

        def apply_filter(query):
            """Apply cursor filtering to the user-list query."""
            return apply_id_cursor_filter(
                query,
                pagination,
                id_column=User.id,
                direction=sort_direction,
            )

        def apply_order(query):
            """Apply stable id ordering for user pagination."""
            return apply_id_ordering(
                query,
                id_column=User.id,
                direction=sort_direction,
            )

        rows = await iam_repository.list_users_with_profile(
            db,
            search=search,
            is_active=is_active,
            query_filter_fn=apply_filter,
            query_order_fn=apply_order,
            limit=pagination.limit + 1,
        )

        role_map = PolicyService.get_org_members_map(org_slug)

        response = to_cursor_page(
            rows,
            pagination,
            serializer=lambda user: self._serialize_user_response(user, role_map.get(user.id, [])),
            next_cursor_builder=build_id_cursor,
        )
        await RedisCache.set(cache_key, response.model_dump(mode="json"), ttl=120)
        return response

    async def user_insights(self, db, *, org_slug: str) -> ApiSuccessResponse[dict[str, int]]:
        """Return aggregate user counts for members of an organization."""
        role_map = PolicyService.get_org_members_map(org_slug)
        member_user_ids = list(role_map.keys())

        total_users = len(member_user_ids)
        if total_users == 0:
            return ApiSuccessResponse[dict[str, int]](
                message="User insights fetched successfully",
                data={"total": 0, "active": 0, "inactive": 0, "superusers": 0},
            )

        active_users = await iam_repository.get_active_users_count(db, member_user_ids)
        superusers = await iam_repository.get_superusers_count(db, member_user_ids)
        inactive_users = total_users - active_users

        return ApiSuccessResponse[dict[str, int]](
            message="User insights fetched successfully",
            data={
                "total": total_users,
                "active": int(active_users),
                "inactive": int(inactive_users),
                "superusers": int(superusers),
            },
        )

    async def upload_avatar(
        self,
        db,
        *,
        current_user: User,
        org_slug: str | None,
        file: UploadFile,
    ) -> UserResponse:
        """Validate, store, and persist a user's avatar image."""
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        max_size = settings.MAX_AVATAR_SIZE_MB * 1024 * 1024

        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type}. Allowed: jpeg, png, gif, webp",
            )

        contents = await file.read()
        if len(contents) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size is {settings.MAX_AVATAR_SIZE_MB} MB",
            )

        ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"
        filename = f"{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
        relative_path = f"avatars/{filename}"

        if current_user.profile and current_user.profile.avatar_url:
            delete_media(current_user.profile.avatar_url)

        image_url = save_media_bytes(relative_path, contents, content_type=file.content_type)
        current_user = await iam_repository.upsert_user_avatar(
            db,
            user=current_user,
            avatar_url=image_url,
        )

        await self.invalidate_user_cache(current_user.id)
        roles = PolicyService.get_user_org_roles(current_user.id, org_slug or "global")
        return self._serialize_user_response(current_user, roles)

    async def get_user(self, db, *, user_id: HashId, org_slug: str | None) -> UserResponse:
        """Return a user's profile by id with optional organization role context."""
        cache_key = f"user:profile:{user_id}"
        cached = await RedisCache.get(cache_key)
        if cached:
            return UserResponse.model_validate(cached)

        user = await iam_repository.get_user_with_profile(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        roles = PolicyService.get_user_org_roles(user.id, org_slug or "global")
        response = self._serialize_user_response(user, roles)
        await RedisCache.set(cache_key, response.model_dump(mode="json"), ttl=300)
        return response

    async def update_current_user(self, db, *, current_user: User, user_update: UserUpdate) -> UserResponse:
        """Update mutable fields for the current authenticated user."""
        if user_update.email is not None:
            if await iam_repository.get_user_email_in_use(db, user_update.email, current_user.id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        current_user = await iam_repository.update_current_user_fields(
            db,
            user=current_user,
            email=user_update.email,
            first_name=user_update.first_name,
            last_name=user_update.last_name,
            phone=user_update.phone,
        )

        await self.invalidate_user_cache(current_user.id)
        await self.invalidate_user_listing_cache()
        return UserResponse.model_validate(current_user)

    async def update_user(self, db, *, user_id: HashId, user_update: UserUpdate) -> UserResponse:
        """Update mutable fields for any user by id."""
        user = await iam_repository.get_user_with_profile(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user_update.email is not None:
            if await iam_repository.get_user_email_in_use(db, user_update.email, user_id):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
            
        await iam_repository.update_user_with_profile_fields(
            db,
            user=user,
            email=user_update.email,
            first_name=user_update.first_name,
            last_name=user_update.last_name,
            phone=user_update.phone,
        )

        user = await iam_repository.get_user_with_profile(db, user_id)
        assert user is not None

        await self.invalidate_user_cache(user.id)
        await self.invalidate_user_listing_cache()
        return UserResponse.model_validate(user)

    async def delete_user(self, db, *, user_id: HashId, current_user_id: int) -> dict[str, str]:
        """Delete a target user unless it is the current caller's own account."""
        if user_id == current_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

        user = await iam_repository.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await iam_repository.delete_user(db, user)
        await iam_repository.commit(db)

        await self.invalidate_user_cache(user.id)
        await self.invalidate_user_listing_cache()
        return {"message": "User deleted successfully"}


user_service = UserService()
