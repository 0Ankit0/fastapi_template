from __future__ import annotations

from typing import Any

from src.apps.communication.services.communications import communications_service
from src.apps.iam.models.user import User
from src.apps.notification.models.notification import Notification
from src.apps.notification.models.notification_preference import NotificationPreference
from src.apps.notification.repositories.notifications import notification_repository
from src.apps.notification.schemas.notification import NotificationCreate
from src.apps.notification.schemas.notification import NotificationResponse
from src.apps.notification.schemas.notification_preference import NotificationPreferenceUpdate
from src.core.exceptions import NotFoundError
from src.core.pagination import (
    CursorSortDirection,
    apply_datetime_id_cursor_filter,
    apply_ordering,
    build_datetime_id_cursor,
    to_cursor_page,
)
from src.core.schemas import CursorPage, CursorPagination
from src.core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    async def get_or_create_preference(self, db, user_id: int) -> NotificationPreference:
        """Return notification preferences for a user, creating defaults when absent."""
        preference = await notification_repository.get_preference(db, user_id)
        if preference is None:
            preference = await notification_repository.create_preference(db, user_id)
        return preference

    async def create_notification(self, db, data: NotificationCreate) -> Notification:
        """Persist a new notification and trigger delivery fan-out."""
        notification = await notification_repository.create_notification_and_commit(db, data)

        await self.dispatch_notification(db, notification)
        return notification

    async def get_for_user(self, db, user_id: int, notification_id: int) -> Notification | None:
        """Return one notification scoped to a specific user."""
        return await notification_repository.get_for_user(db, user_id, notification_id)

    async def list_notifications(
        self,
        db,
        *,
        user_id: int,
        pagination: CursorPagination,
        is_read: bool | None,
        sort_direction: CursorSortDirection,
    ) -> CursorPage[NotificationResponse]:
        """Return paginated notifications for a user with optional read filter."""
        def apply_filter(q):
            """Apply cursor filtering to notification query."""
            return apply_datetime_id_cursor_filter(
                q,
                pagination,
                datetime_column=Notification.created_at,
                id_column=Notification.id,
                direction=sort_direction,
            )
        
        def apply_order(q):
            """Apply stable ordering for notification pagination."""
            return apply_ordering(
                q,
                order_column=Notification.created_at,
                id_column=Notification.id,
                direction=sort_direction,
            )

        rows = await notification_repository.list_notifications_paginated(
            db,
            user_id=user_id,
            is_read=is_read,
            query_filter_fn=apply_filter,
            query_order_fn=apply_order,
            limit=pagination.limit + 1,
        )
        return to_cursor_page(
            rows,
            pagination,
            serializer=NotificationResponse.model_validate,
            next_cursor_builder=build_datetime_id_cursor,
        )

    async def dispatch_notification(self, db, notification: Notification) -> None:
        """Deliver a notification via realtime, email, and push channels."""
        preference = await self.get_or_create_preference(db, notification.user_id)
        user = await notification_repository.get_user(db, notification.user_id)

        payload = {
            "event": "notification.created",
            "id": str(notification.id),
            "data": {
                "id": notification.id,
                "user_id": notification.user_id,
                "title": notification.title,
                "body": notification.body,
                "notification_type": notification.notification_type.value,
                "is_read": notification.is_read,
                "read_at": notification.read_at.isoformat() if notification.read_at else None,
                "extra_data": notification.extra_data,
                "created_at": notification.created_at.isoformat(),
                "updated_at": notification.updated_at.isoformat(),
            },
        }

        delivered = 0
        if preference.websocket_enabled or preference.sse_enabled:
            from src.apps.realtime.manager import manager

            delivered = await manager.send_to_user(notification.user_id, payload)

        if preference.email_enabled and user:
            await communications_service.send_email(
                subject=notification.title,
                recipients=[{"name": user.username, "email": str(user.email)}],
                template_name="notification",
                context={
                    "html_body": (
                        f"<h1>{notification.title}</h1><p>{notification.body}</p>"
                    ),
                    "text_body": f"{notification.title}\n\n{notification.body}",
                },
                inline_template=True,
            )

        if preference.push_enabled:
            communications_service.send_push(
                {
                    "provider": preference.push_provider,
                    "title": notification.title,
                    "body": notification.body,
                    "user_id": notification.user_id,
                    "type": notification.notification_type.value,
                    "extra_data": notification.extra_data,
                }
            )

        logger.info(
            "notification_dispatched id=%s user_id=%s realtime_deliveries=%s",
            notification.id,
            notification.user_id,
            delivered,
        )

    async def mark_as_read(self, db, notification_id: int, user_id: int) -> Notification:
        """Mark a user's notification as read if it is unread."""
        notification = await notification_repository.get_for_user(db, user_id, notification_id)
        if notification is None:
            raise NotFoundError("Notification not found")

        if not notification.is_read:
            notification = await notification_repository.mark_as_read(db, notification)

        return notification

    async def update_preferences(self, db, *, user_id: int, data: NotificationPreferenceUpdate) -> NotificationPreference:
        """Update a user's notification preferences and persist changes."""
        preference = await self.get_or_create_preference(db, user_id)
        updates = data.model_dump(exclude_none=True)
        return await notification_repository.update_preference_and_commit(
            db,
            preference=preference,
            updates=updates,
        )


notification_service = NotificationService()
