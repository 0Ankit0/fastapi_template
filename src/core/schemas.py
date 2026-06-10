from typing import Any

from pydantic import BaseModel, Field


class DeliveryResult(BaseModel):
    channel: str
    provider: str
    success: bool
    message_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
