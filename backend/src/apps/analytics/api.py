"""Analytics API endpoints.

Provides server-side feature-flag resolution so clients don't need to
embed PostHog API keys.  All endpoints require authentication.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from src.apps.analytics.dependencies import get_analytics
from src.apps.analytics.events import PaymentEvents
from src.apps.analytics.service import AnalyticsService
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.analytics.schemas.graphql_analytics import (
    FeatureFlag,
    FeatureFlags,
    SubscriptionResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@strawberry.type
class Query:
    @strawberry.field
    async def feature_flags(self, info: Info) -> FeatureFlags:
        ctx = info.context
        current_user: User = ctx["current_user"]
        analytics: AnalyticsService = ctx["analytics"]

        flags = await analytics.get_all_feature_flags(str(current_user.id))
        return FeatureFlags(flags=flags, analytics_enabled=analytics.enabled)

    @strawberry.field
    async def feature_flag(self, info: Info, flag_key: str) -> FeatureFlag:
        ctx = info.context
        current_user: User = ctx["current_user"]
        analytics: AnalyticsService = ctx["analytics"]

        value = await analytics.get_feature_flag(str(current_user.id), flag_key)
        return FeatureFlag(flag_key=flag_key, value=value, analytics_enabled=analytics.enabled)


async def get_graphql_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analytics: AnalyticsService = Depends(get_analytics),
) -> dict:
    """Expose FastAPI dependencies to Strawberry resolvers."""
    return {"current_user": current_user, "db": db, "analytics": analytics}


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def apply_for_subscription(self, info: Info, plan: str) -> SubscriptionResponse:
        """Track that a user has applied for a subscription (analytics event)."""
        ctx = info.context
        current_user: User = ctx["current_user"]
        analytics: AnalyticsService = ctx["analytics"]

        if current_user.id is None:
            return SubscriptionResponse(applied=False, message="Missing authenticated user")

        try:
            await analytics.capture(
                str(current_user.id),
                PaymentEvents.SUBSCRIPTION_STARTED,
                {"plan": plan},
            )
            return SubscriptionResponse(applied=True, message="Subscription applied")
        except Exception as exc:
            return SubscriptionResponse(applied=False, message=str(exc))


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=get_graphql_context)
