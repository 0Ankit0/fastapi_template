from __future__ import annotations

from fastapi import APIRouter, Depends

from src.apps.iam.models.user import User
from src.apps.notification.models.notification_preference import NotificationPreference
from src.apps.notification.schemas.notification_preference import (
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from src.core.dependencies import DB, get_current_user
from src.core.schemas import ApiSuccessResponse

from src.apps.notification.services.notifications import notification_service

router = APIRouter(
    prefix="/notifications/preferences",
    tags=["Notification Preferences"],
)


@router.get(
    "/",
    response_model=ApiSuccessResponse[NotificationPreferenceRead],
    summary="Get notification preferences",
    description="Returns the authenticated user's notification channel preferences, creating defaults when missing.",
)
async def get_preferences(
    db: DB,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[NotificationPreferenceRead]:
    preference = await notification_service.get_or_create_preference(db, current_user.id)
    return ApiSuccessResponse(
        message="Notification preferences fetched successfully",
        data=NotificationPreferenceRead.model_validate(preference),
    )


@router.patch(
    "/",
    response_model=ApiSuccessResponse[NotificationPreferenceRead],
    summary="Update notification preferences",
    description="Updates the authenticated user's notification delivery preferences.",
)
async def update_preferences(
    data: NotificationPreferenceUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[NotificationPreferenceRead]:
    preference = await notification_service.update_preferences(
        db,
        user_id=current_user.id,
        data=data,
    )

    return ApiSuccessResponse(
        message="Notification preferences updated successfully",
        data=NotificationPreferenceRead.model_validate(preference),
    )
