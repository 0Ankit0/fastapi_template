from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from src.apps.notification.models.notification import NotificationType
from src.core.schemas import BaseSchema
from src.core.types import HashId


class NotificationBase(BaseSchema):
    title: str = Field(
        ...,
        max_length=255,
        description="Short notification title shown in the UI or email subject.",
    )
    body: str = Field(
        ...,
        description="Main notification body text.",
    )
    notification_type: NotificationType = Field(
        default=NotificationType.INFO,
        description="Notification classification used for styling and routing.",
    )
    extra_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured metadata attached to the notification.",
    )


class NotificationCreate(NotificationBase):
    user_id: HashId = Field(
        ...,
        description="Recipient user identifier.",
    )


class NotificationUpdate(BaseSchema):
    is_read: bool | None = Field(
        default=None,
        description="Mark the notification as read or unread.",
    )


class NotificationResponse(NotificationBase):
    id: HashId = Field(
        ...,
        description="Notification identifier.",
    )
    user_id: HashId = Field(
        ...,
        description="Recipient user identifier.",
    )
    is_read: bool = Field(
        default=False,
        description="Whether the notification has been read.",
    )
    read_at: datetime | None = Field(
        default=None,
        description="When the notification was marked as read.",
    )
    created_at: datetime = Field(
        ...,
        description="When the notification record was created.",
    )
    updated_at: datetime = Field(
        ...,
        description="When the notification record was last updated.",
    )
