"""Notification service — persist + real-time WebSocket delivery."""
import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.notification.models.notification import Notification, NotificationType
from src.apps.notification.schemas.notification import (
    NotificationCreate,
    NotificationList,
    NotificationRead,
)

log = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    data: NotificationCreate,
    push_ws: bool = True,
) -> Notification:
    """
    Persist a notification and optionally push it to the user via WebSocket.

    The WebSocket push is best-effort: if the user is not connected, it is
    silently skipped (the notification is still saved to the database).
    """
    notification = Notification(
        user_id=data.user_id,
        title=data.title,
        body=data.body,
        type=data.type,
        extra_data=data.extra_data,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    if push_ws:
        await _push_to_ws(notification)

    return notification


async def _push_to_ws(notification: Notification) -> None:
    """Push notification to the user's active WebSocket connections (if any)."""
    try:
        from src.apps.websocket.manager import manager

        await manager.push_event(
            user_id=notification.user_id,
            event="notification.new",
            data={
                "id": notification.id,
                "title": notification.title,
                "body": notification.body,
                "type": notification.type,
                "is_read": notification.is_read,
                "extra_data": notification.extra_data,
                "created_at": notification.created_at.isoformat(),
            },
        )
    except Exception as exc:
        log.warning("WS push failed for notification id=%s: %s", notification.id, exc)


async def get_user_notifications(
    db: AsyncSession,
    user_id: int,
    *,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> NotificationList:
    """Return paginated notifications for a user."""
    base_query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        base_query = base_query.where(Notification.is_read == False)  # noqa: E712

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    unread_result = await db.execute(
        select(func.count()).select_from(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .subquery()
        )
    )
    unread_count = unread_result.scalar_one()

    result = await db.execute(
        base_query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    return NotificationList(
        items=[NotificationRead.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
    )


async def get_notification(
    db: AsyncSession,
    notification_id: int,
    user_id: int,
) -> Optional[Notification]:
    """Fetch a single notification belonging to the given user."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    return result.scalars().first()


async def mark_as_read(
    db: AsyncSession,
    notification_id: int,
    user_id: int,
) -> Optional[Notification]:
    """Mark a single notification as read. Returns None if not found."""
    notification = await get_notification(db, notification_id, user_id)
    if not notification:
        return None
    notification.is_read = True
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    return notification


async def mark_all_read(db: AsyncSession, user_id: int) -> int:
    """Mark all unread notifications for a user as read. Returns the count updated."""
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    notifications = result.scalars().all()
    for n in notifications:
        n.is_read = True
        db.add(n)
    await db.commit()
    return len(notifications)


async def delete_notification(
    db: AsyncSession,
    notification_id: int,
    user_id: int,
) -> bool:
    """Delete a notification. Returns True if deleted, False if not found."""
    notification = await get_notification(db, notification_id, user_id)
    if not notification:
        return False
    await db.delete(notification)
    await db.commit()
    return True
