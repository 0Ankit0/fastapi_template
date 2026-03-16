
# GraphQL Token Management
from fastapi import APIRouter
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.schemas.token_tracking import TokenTrackingResponse
from src.apps.iam.schemas.graphql_token_tracking import TokenTrackingType
from src.apps.iam.api.deps import get_db, get_current_user
from src.apps.core.cache import RedisCache
from src.apps.analytics.service import AnalyticsService
from src.apps.analytics.events import UserEvents
from datetime import datetime, timezone
from sqlmodel import select, desc, col, func
from graphql import GraphQLError
from src.apps.iam.utils.hashid import decode_id_or_404

router = APIRouter()

@strawberry.type
class Query:
    @strawberry.field
    async def active_tokens(self, info: Info, skip: int = 0, limit: int = 10) -> List[TokenTrackingType]:
        db: AsyncSession = info.context["db"]
        current_user = info.context["current_user"]
        query = select(TokenTracking).where(
            TokenTracking.user_id == current_user.id,
            TokenTracking.is_active
        ).order_by(desc(col(TokenTracking.created_at))).offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()
        return [TokenTrackingType.from_orm(item) for item in items]

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def revoke_token(self, info: Info, token_id: str) -> bool:
        db: AsyncSession = info.context["db"]
        current_user = info.context["current_user"]
        tid = decode_id_or_404(token_id)
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.id == tid,
                TokenTracking.user_id == current_user.id
            )
        )
        token_tracking = result.scalars().first()
        if not token_tracking:
            raise GraphQLError("Token not found")
        if not token_tracking.is_active:
            raise GraphQLError("Token is already revoked")
        token_tracking.is_active = False
        token_tracking.revoked_at = datetime.now(timezone.utc)
        token_tracking.revoke_reason = "Revoked by user"
        await db.commit()
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
        return True

    @strawberry.mutation
    async def revoke_all_tokens(self, info: Info) -> int:
        db: AsyncSession = info.context["db"]
        current_user = info.context["current_user"]
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
            token_tracking.revoke_reason = "All tokens revoked by user"
        await db.commit()
        await RedisCache.clear_pattern(f"tokens:active:{current_user.id}:*")
        return len(tokens)

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema)
