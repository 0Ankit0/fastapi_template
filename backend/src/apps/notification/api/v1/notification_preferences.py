"""Notification preference and push-device API."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.communications import get_communications_service
from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.notification.schemas.notification_device import (
    NotificationDeviceCreate,
    NotificationDeviceRead,
)
from src.apps.notification.schemas.notification_preference import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    PushSubscriptionUpdate,
)
from src.apps.notification.services.notification import (
    get_or_create_preference,
    list_devices,
    register_device,
    remove_device,
    remove_webpush_subscription,
)

router = APIRouter()


def _preference_response(pref) -> NotificationPreferenceRead:
    data = NotificationPreferenceRead.model_validate(pref).model_dump()
    data["push_provider"] = "webpush" if pref.push_endpoint else None
    return NotificationPreferenceRead.model_validate(data)


@router.get("/preferences/", response_model=NotificationPreferenceRead)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceRead:
    assert isinstance(current_user.id, int), "User Id can't be None"
    pref = await get_or_create_preference(db, current_user.id)
    return _preference_response(pref)


@router.patch("/preferences/", response_model=NotificationPreferenceRead)
async def update_preferences(
    data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceRead:
    assert isinstance(current_user.id, int), "User Id can't be None"
    pref = await get_or_create_preference(db, current_user.id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(pref, field, value)
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return _preference_response(pref)


@router.get("/devices/", response_model=list[NotificationDeviceRead])
async def get_notification_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationDeviceRead]:
    assert isinstance(current_user.id, int), "User Id can't be None"
    devices = await list_devices(db, current_user.id)
    return [NotificationDeviceRead.model_validate(device) for device in devices]


@router.post("/devices/", response_model=NotificationDeviceRead, status_code=status.HTTP_201_CREATED)
async def create_notification_device(
    data: NotificationDeviceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationDeviceRead:
    assert isinstance(current_user.id, int), "User Id can't be None"
    device = await register_device(db, current_user.id, data)
    pref = await get_or_create_preference(db, current_user.id)
    pref.push_enabled = True
    db.add(pref)
    await db.commit()
    return NotificationDeviceRead.model_validate(device)


@router.delete("/devices/{device_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    assert isinstance(current_user.id, int), "User Id can't be None"
    await remove_device(db, current_user.id, device_id)


@router.get("/push/config/")
async def get_push_config() -> dict:
    return get_communications_service().get_push_public_config()


@router.put("/preferences/push-subscription/", response_model=NotificationPreferenceRead)
async def register_push_subscription(
    data: PushSubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceRead:
    assert isinstance(current_user.id, int), "User Id can't be None"
    await register_device(
        db,
        current_user.id,
        NotificationDeviceCreate(
            provider="webpush",
            platform="web",
            endpoint=data.endpoint,
            p256dh=data.p256dh,
            auth=data.auth,
        ),
    )
    pref = await get_or_create_preference(db, current_user.id)
    pref.push_enabled = True
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return _preference_response(pref)


@router.delete("/preferences/push-subscription/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_push_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    assert isinstance(current_user.id, int), "User Id can't be None"
    await remove_webpush_subscription(db, current_user.id)
