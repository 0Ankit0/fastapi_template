"""GraphQL schema + resolvers for notifications."""

from fastapi import APIRouter, Depends
import strawberry
from graphql import GraphQLError
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.notification.schemas.notification import NotificationList, NotificationRead
from src.apps.notification.schemas.graphql_notification import NotificationListType, NotificationItemType
from src.apps.notification.schemas.graphql_notification_preference import (
    NotificationPreferenceType,
    NotificationPreferenceUpdateInput,
    PushSubscriptionUpdateInput,
)
from src.apps.notification.services.notification import (
    get_notification,
    get_user_notifications,
    mark_all_read,
    mark_as_read,
)
from src.apps.notification.models.notification_preference import NotificationPreference


async def get_graphql_context(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Expose FastAPI dependencies to Strawberry resolvers."""
    return {"current_user": current_user, "db": db}


async def _get_or_create_pref(db: AsyncSession, user_id: int) -> NotificationPreference:
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    pref = result.scalars().first()
    if pref is None:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return pref


@strawberry.type
class Query:
    @strawberry.field
    async def notifications(
        self,
        info: Info,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> NotificationListType:
        """Fetch paginated notifications for the authenticated user."""
        try:
            ctx = info.context
            current_user: User = ctx["current_user"]
            db: AsyncSession = ctx["db"]

            if current_user.id is None:
                raise GraphQLError("Authenticated user ID is missing")

            notifications = await get_user_notifications(
                db, current_user.id, unread_only=unread_only, skip=skip, limit=limit
            )
            return NotificationListType.from_pydantic(notifications)
        except Exception as exc:
            raise GraphQLError(str(exc))

    @strawberry.field
    async def notification_preferences(self, info: Info) -> NotificationPreferenceType:
        """Fetch a user's notification preferences."""
        try:
            ctx = info.context
            current_user: User = ctx["current_user"]
            db: AsyncSession = ctx["db"]

            if current_user.id is None:
                raise GraphQLError("Authenticated user ID is missing")

            pref = await _get_or_create_pref(db, current_user.id)
            return NotificationPreferenceType.from_pydantic(pref)
        except Exception as exc:
            raise GraphQLError(str(exc))

    @strawberry.field
    async def notification(self, info: Info, notification_id: int) -> NotificationItemType | None:
        """Fetch a single notification for the authenticated user."""
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        if current_user.id is None:
            raise GraphQLError("Authenticated user ID is missing")

        notification = await get_notification(db, notification_id, current_user.id)
        if not notification:
            return None

        # Convert ORM model -> Pydantic model, then to Strawberry type
        dto = NotificationRead.model_validate(notification)
        return NotificationItemType(**dto.model_dump())


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def mark_notification_read(self, info: Info, notification_id: int) -> NotificationItemType | None:
        """Mark a single notification as read."""
        ctx = info.context
        current_user: User = ctx["current_user"]
        db: AsyncSession = ctx["db"]

        if current_user.id is None:
            raise GraphQLError("Authenticated user ID is missing")

        notification = await mark_as_read(db, notification_id, current_user.id)
        if not notification:
            return None
        dto = NotificationRead.model_validate(notification)
        return NotificationItemType(**dto.model_dump())

    @strawberry.mutation
    async def mark_all_notifications_read(self, info: Info) -> int:
        """Mark all notifications as read for the authenticated user."""
        try:
            ctx = info.context
            current_user: User = ctx["current_user"]
            db: AsyncSession = ctx["db"]

            if current_user.id is None:
                raise GraphQLError("Authenticated user ID is missing")

            count = await mark_all_read(db, current_user.id)
            return count
        except Exception as exc:
            raise GraphQLError(str(exc))

    @strawberry.mutation
    async def update_notification_preferences(
        self, info: Info, input: NotificationPreferenceUpdateInput
    ) -> NotificationPreferenceType:
        """Update a user's notification preferences."""
        try:
            ctx = info.context
            current_user: User = ctx["current_user"]
            db: AsyncSession = ctx["db"]

            if current_user.id is None:
                raise GraphQLError("Authenticated user ID is missing")

            pref = await _get_or_create_pref(db, current_user.id)
            for field, value in input.__dict__.items():
                if value is not None:
                    setattr(pref, field, value)

            db.add(pref)
            await db.commit()
            await db.refresh(pref)
            return NotificationPreferenceType.from_pydantic(pref)
        except Exception as exc:
            raise GraphQLError(str(exc))

    @strawberry.mutation
    async def register_push_subscription(
        self, info: Info, input: PushSubscriptionUpdateInput
    ) -> NotificationPreferenceType:
        """Register a browser push subscription and enable push notifications."""
        try:
            ctx = info.context
            current_user: User = ctx["current_user"]
            db: AsyncSession = ctx["db"]

            if current_user.id is None:
                raise GraphQLError("Authenticated user ID is missing")

            pref = await _get_or_create_pref(db, current_user.id)
            pref.push_endpoint = input.endpoint
            pref.push_p256dh = input.p256dh
            pref.push_auth = input.auth
            pref.push_enabled = True

            db.add(pref)
            await db.commit()
            await db.refresh(pref)
            return NotificationPreferenceType.from_pydantic(pref)
        except Exception as exc:
            raise GraphQLError(str(exc))

    @strawberry.mutation
    async def remove_push_subscription(self, info: Info) -> NotificationPreferenceType:
        """Remove a user's browser push subscription."""
        try:
            ctx = info.context
            current_user: User = ctx["current_user"]
            db: AsyncSession = ctx["db"]

            if current_user.id is None:
                raise GraphQLError("Authenticated user ID is missing")

            pref = await _get_or_create_pref(db, current_user.id)
            pref.push_endpoint = None
            pref.push_p256dh = None
            pref.push_auth = None
            pref.push_enabled = False

            db.add(pref)
            await db.commit()
            await db.refresh(pref)
            return NotificationPreferenceType.from_pydantic(pref)
        except Exception as exc:
            raise GraphQLError(str(exc))


schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_router = GraphQLRouter(schema, context_getter=get_graphql_context)


