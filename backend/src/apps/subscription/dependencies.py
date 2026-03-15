"""
Legacy subscription dependencies.

- ``require_active_subscription`` is still provided here for use by
  subscription-related endpoints.  It enforces that the current user has
  an active (non-expired) subscription, raising HTTP 402 otherwise.

The tenant-scoped helpers used to live here but have been moved into the
``multitenancy`` module; import ``_require_tenant_role`` or the public
APIs in ``src.apps.multitenancy.api.v1.tenant`` instead.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.api.deps import get_db, get_current_user as get_current_active_user
from src.apps.iam.models.user import User
from src.apps.subscription.services.subscription_service import (
    get_subscription,
    is_subscription_active,
)


async def require_active_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Gate owner‑dashboard endpoints behind an active subscription.

    Superusers bypass this check (they are the platform operator).
    Raises 402 Payment Required if subscription is inactive/expired.
    """
    if getattr(current_user, "is_superuser", False):
        return current_user

    sub = await get_subscription(db, current_user.id)
    if not is_subscription_active(sub):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "subscription_required",
                "message": (
                    "Your subscription has expired or is not active. "
                    "Please subscribe or renew to access the owner dashboard."
                ),
                "subscription_status": sub.status.value if sub else "none",
            },
        )
    return current_user
