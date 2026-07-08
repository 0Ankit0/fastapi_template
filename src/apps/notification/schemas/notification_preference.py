from __future__ import annotations

from pydantic import Field

from src.core.schemas import BaseSchema
from src.core.types import HashId


class NotificationPreferenceBase(BaseSchema):
    websocket_enabled: bool = Field(
        default=True,
        description="Deliver in-app notifications over WebSockets.",
    )
    sse_enabled: bool = Field(
        default=True,
        description="Deliver in-app notifications over server-sent events.",
    )
    email_enabled: bool = Field(
        default=False,
        description="Send notification copies by email.",
    )
    push_enabled: bool = Field(
        default=False,
        description="Send notification copies through the configured push provider.",
    )
    push_provider: str | None = Field(
        default=None,
        max_length=32,
        description="Optional push provider override for this user.",
    )


class NotificationPreferenceRead(NotificationPreferenceBase):
    id: HashId = Field(
        ...,
        description="Preference row identifier.",
    )
    user_id: HashId = Field(
        ...,
        description="Owning user identifier.",
    )


class NotificationPreferenceUpdate(BaseSchema):
    websocket_enabled: bool | None = Field(
        default=None,
        description="Enable or disable WebSocket delivery.",
    )
    sse_enabled: bool | None = Field(
        default=None,
        description="Enable or disable SSE delivery.",
    )
    email_enabled: bool | None = Field(
        default=None,
        description="Enable or disable email delivery.",
    )
    push_enabled: bool | None = Field(
        default=None,
        description="Enable or disable push delivery.",
    )
    push_provider: str | None = Field(
        default=None,
        max_length=32,
        description="Optional push provider override.",
    )
