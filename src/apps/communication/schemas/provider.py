from src.core.schemas import BaseSchema
from pydantic import Field
from typing import Any

class ProviderStatus(BaseSchema):
    channel: str
    provider: str
    active: bool = False
    enabled: bool = False
    configured: bool = False
    fallback: bool = False
    details: dict[str, Any] = Field(default_factory=dict)
