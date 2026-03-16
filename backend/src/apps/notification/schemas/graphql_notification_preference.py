import strawberry
from typing import Optional

from src.apps.notification.schemas.notification_preference import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    PushSubscriptionUpdate,
)


@strawberry.experimental.pydantic.type(model=NotificationPreferenceRead, all_fields=True)
class NotificationPreferenceType:
    """GraphQL representation of a user's notification preferences."""


@strawberry.input
class NotificationPreferenceUpdateInput:
    websocket_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None


@strawberry.input
class PushSubscriptionUpdateInput:
    endpoint: str
    p256dh: str
    auth: str
