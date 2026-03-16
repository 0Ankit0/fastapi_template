
# GraphQL Password Management
from fastapi import APIRouter
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.iam.models.user import User
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.api.deps import get_db, get_current_user
from src.apps.core.cache import RedisCache
from src.apps.core import security
from src.apps.core.security import TokenType
from src.apps.core.config import settings
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import AuthEvents
from sqlmodel import select
from datetime import datetime, timezone
from graphql import GraphQLError

from src.apps.iam.schemas.graphql_password import (
    PasswordResetConfirmInput,
    PasswordResetRequestInput,
    ChangePasswordInput,
)

router = APIRouter()

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def request_password_reset(self, info: Info, input: PasswordResetRequestInput) -> bool:
        db: AsyncSession = info.context["db"]
        analytics: AnalyticsService = info.context.get("analytics")
        result = await db.execute(select(User).where(User.email == input.email))
        user = result.scalars().first()
        if not user:
            return True
        reset_token = security.create_password_reset_token(user.id)
        from src.apps.iam.services.email import EmailService
        await EmailService.send_password_reset_email(user, reset_token)
        if analytics:
            await analytics.capture(str(user.id), AuthEvents.PASSWORD_RESET_REQUESTED)
        return True

    @strawberry.mutation
    async def confirm_password_reset(self, info: Info, input: PasswordResetConfirmInput) -> bool:
        db: AsyncSession = info.context["db"]
        analytics: AnalyticsService = info.context.get("analytics")
        from src.apps.iam.models.used_token import UsedToken
        try:
            token_data = security.verify_secure_url_token(input.token)
        except Exception:
            raise GraphQLError("Invalid or expired reset link")
        user_id = token_data.get("user_id")
        jwt_token = token_data.get("token")
        purpose = token_data.get("purpose")
        if not all([user_id, jwt_token]) or purpose != "password_reset":
            raise GraphQLError("Invalid reset token data")
        payload = security.verify_token(jwt_token, token_type=TokenType.PASSWORD_RESET)
        token_jti = payload.get("jti")
        if str(payload.get("sub")) != str(user_id):
            raise GraphQLError("Token data mismatch - possible tampering detected")
        if token_jti:
            used_check = await db.execute(
                select(UsedToken).where(UsedToken.token_jti == token_jti)
            )
            if used_check.scalars().first():
                raise GraphQLError("This password reset link has already been used")
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        if not user:
            raise GraphQLError("User not found")
        user.hashed_password = security.get_password_hash(input.new_password)
        if token_jti:
            used_token = UsedToken(
                token_jti=token_jti,
                user_id=int(user_id),
                token_purpose="password_reset"
            )
            db.add(used_token)
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.user_id == user.id,
                TokenTracking.is_active
            )
        )
        tokens = result.scalars().all()
        for token_tracking in tokens:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = "Password reset"
        await db.commit()
        await RedisCache.delete(f"user:profile:{user_id}")
        await RedisCache.clear_pattern(f"tokens:active:{user_id}:*")
        if analytics:
            await analytics.capture(str(user_id), AuthEvents.PASSWORD_RESET_COMPLETED)
        return True

    @strawberry.mutation
    async def change_password(self, info: Info, input: ChangePasswordInput) -> bool:
        db: AsyncSession = info.context["db"]
        current_user: User = info.context["current_user"]
        analytics: AnalyticsService = info.context.get("analytics")
        if not security.verify_password(input.current_password, current_user.hashed_password):
            raise GraphQLError("Incorrect current password")
        current_user.hashed_password = security.get_password_hash(input.new_password)
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.user_id == current_user.id,
                TokenTracking.is_active
            )
        )
        tokens = result.scalars().all()
        for token_tracking in tokens:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = "Password changed"
        await db.commit()
        await RedisCache.delete(f"user:profile:{current_user.id}")
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
        if analytics:
            await analytics.capture(str(current_user.id), AuthEvents.PASSWORD_CHANGED)
        return True

@strawberry.type
class Query:
    """Minimal query type required by Strawberry (unused)."""

    @strawberry.field
    def ping(self) -> str:
        return "pong"

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema)
