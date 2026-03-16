import strawberry
from datetime import datetime
from typing import Optional, List
from strawberry.scalars import JSON

from src.apps.notification.schemas.notification import NotificationList
from src.apps.notification.models.notification import NotificationType


@strawberry.type
class NotificationItemType:
    """GraphQL representation of a notification."""
    id: int
    user_id: int
    title: str
    body: str
    type: NotificationType
    is_read: bool
    extra_data: Optional[JSON]
    created_at: datetime


@strawberry.type
class NotificationListType:
    """GraphQL representation of a paginated notification list."""
    items: List[NotificationItemType]
    total: int
    unread_count: int
