import strawberry
from typing import Any, Optional
from strawberry.scalars import JSON


@strawberry.type
class FeatureFlags:
    flags: JSON
    analytics_enabled: bool


@strawberry.type
class FeatureFlag:
    flag_key: str
    value: JSON
    analytics_enabled: bool


@strawberry.type
class SubscriptionResponse:
    """Result of a subscription request."""

    applied: bool
    message: Optional[str] = None
