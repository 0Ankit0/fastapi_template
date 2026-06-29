from pydantic import Field
from typing import Any
from src.core.schemas import BaseSchema

class DeliveryResult(BaseSchema):
    channel: str
    provider: str
    success: bool
    message_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
