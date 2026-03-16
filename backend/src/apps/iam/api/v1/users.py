"""
User management endpoints with caching and pagination
"""
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File

# GraphQL User Management
import strawberry

router = APIRouter()
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from typing import Any, List, Optional, cast
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.iam.models.user import User
from src.apps.iam.schemas.user import UserResponse, UserUpdate
from src.apps.iam.schemas.graphql_user import UserType, UserUpdateInput
from src.apps.iam.api.deps import get_db, get_current_user, get_current_active_superuser
from src.apps.iam.utils.hashid import decode_id_or_404
from src.apps.core.cache import RedisCache
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import UserEvents
from src.apps.core.config import settings
from sqlmodel import select, func, or_, col
from sqlalchemy.orm import selectinload
from graphql import GraphQLError

@strawberry.type
class Query:
    @strawberry.field
    async def users(
        self, info: Info, skip: int = 0, limit: int = 10, search: Optional[str] = None, is_active: Optional[bool] = None
    ) -> List[UserType]:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        if not current_user.is_superuser:
            raise GraphQLError("Not authorized")
        query = select(User).options(selectinload(cast(Any, User.profile)))
        if search:
            search_filter = or_(
                col(User.email).ilike(f"%{search}%"),
                col(User.username).ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        query = query.offset(skip).limit(limit).order_by(col(User.id))
        result = await db.execute(query)
        items = result.scalars().all()
        return [UserType.from_orm(user) for user in items]

    @strawberry.field
    async def user(self, info: Info, user_id: str) -> UserType:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        if not current_user.is_superuser:
            raise GraphQLError("Not authorized")
        uid = decode_id_or_404(user_id)
        result = await db.execute(
            select(User).options(selectinload(cast(Any, User.profile))).where(User.id == uid)
        )
        user = result.scalars().first()
        if not user:
            raise GraphQLError("User not found")
        return UserType.from_orm(user)

    @strawberry.field
    async def me(self, info: Info) -> UserType:
        current_user: User = info.context["current_user"]
        return UserType.from_orm(current_user)

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def update_me(self, info: Info, input: UserUpdateInput) -> UserType:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        if input.email is not None:
            result = await db.execute(
                select(User).where(
                    User.email == input.email,
                    User.id != current_user.id
                )
            )
            if result.scalars().first():
                raise GraphQLError("Email already registered")
            current_user.email = input.email
            current_user.is_confirmed = False
        if current_user.profile:
            if input.first_name is not None:
                current_user.profile.first_name = input.first_name
            if input.last_name is not None:
                current_user.profile.last_name = input.last_name
            if input.phone is not None:
                current_user.profile.phone = input.phone
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)
        if current_user.profile:
            await db.refresh(current_user.profile)
        await RedisCache.delete(f"user:profile:{current_user.id}")
        await RedisCache.clear_pattern("users:list:*")
        return UserType.from_orm(current_user)

    @strawberry.mutation
    async def update_user(self, info: Info, user_id: str, input: UserUpdateInput) -> UserType:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        if not current_user.is_superuser:
            raise GraphQLError("Not authorized")
        uid = decode_id_or_404(user_id)
        result = await db.execute(
            select(User).options(selectinload(cast(Any, User.profile))).where(User.id == uid)
        )
        user = result.scalars().first()
        if not user:
            raise GraphQLError("User not found")
        if input.email is not None:
            result = await db.execute(
                select(User).where(
                    User.email == input.email,
                    User.id != uid
                )
            )
            if result.scalars().first():
                raise GraphQLError("Email already registered")
            user.email = input.email
        if user.profile:
            if input.first_name is not None:
                user.profile.first_name = input.first_name
            if input.last_name is not None:
                user.profile.last_name = input.last_name
            if input.phone is not None:
                user.profile.phone = input.phone
        db.add(user)
        await db.commit()
        await db.refresh(user)
        if user.profile:
            await db.refresh(user.profile)
        await RedisCache.delete(f"user:profile:{uid}")
        await RedisCache.clear_pattern("users:list:*")
        await RedisCache.clear_pattern(f"user:{uid}:*")
        return UserType.from_orm(user)

    @strawberry.mutation
    async def delete_user(self, info: Info, user_id: str) -> bool:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        uid = decode_id_or_404(user_id)
        if uid == current_user.id:
            raise GraphQLError("Cannot delete your own account")
        result = await db.execute(select(User).where(User.id == uid))
        user = result.scalars().first()
        if not user:
            raise GraphQLError("User not found")
        await db.delete(user)
        await db.commit()
        await RedisCache.delete(f"user:profile:{uid}")
        await RedisCache.clear_pattern("users:list:*")
        await RedisCache.clear_pattern(f"user:{uid}:*")
        await RedisCache.delete(f"casbin:roles:{uid}")
        await RedisCache.delete(f"casbin:permissions:{uid}")
        return True

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema)
