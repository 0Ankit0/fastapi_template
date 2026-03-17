"""Notification preference API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.api.deps import get_current_user, get_db
from src.apps.iam.models.user import User
from src.apps.notification.schemas.notification_preference import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from src.apps.notification.services.notification import (
    get_or_create_preference,
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
