from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import select

from src.apps.notification.models.notification import Notification
from src.apps.notification.schemas.notification import NotificationCreate


class NotificationModelRepository:
    async def get_for_user(self, db, user_id: int, notification_id: int) -> Notification | None:
        """Return a notification by id scoped to a specific user."""
        result = await db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.id == notification_id,
            )
        )
        return result.scalars().first()

    def list_for_user(self, user_id: int, query=None):
        """Apply a user filter to an existing notification query."""
        if query is None:
            query = select(Notification)
        return query.where(Notification.user_id == user_id)

    async def list_notifications_paginated(
        self,
        db,
        user_id: int,
        is_read: bool | None = None,
        query_filter_fn=None,
        query_order_fn=None,
        limit: int = 50,
    ) -> Sequence[Notification]:
        """List user notifications with optional read-state and cursor filters."""
        query = select(Notification).where(Notification.user_id == user_id)

        if is_read is not None:
            query = query.where(Notification.is_read.is_(is_read))

        if query_filter_fn:
            query = query_filter_fn(query)
        if query_order_fn:
            query = query_order_fn(query)

        query = query.limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    def create_notification(self, data: NotificationCreate) -> Notification:
        """Build a new notification entity from the create payload."""
        return Notification(
            user_id=data.user_id,
            title=data.title,
            body=data.body,
            notification_type=data.notification_type,
            extra_data=data.extra_data,
        )

    async def create_notification_and_commit(self, db, data: NotificationCreate) -> Notification:
        """Create, persist, and refresh a notification entity."""
        notification = self.create_notification(data)
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def mark_as_read(self, db, notification: Notification) -> Notification:
        """Mark a notification as read and persist the read timestamp."""
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)
        return notification
