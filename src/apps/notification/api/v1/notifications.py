from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from src.apps.iam.models.user import User
from src.apps.notification.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
)
from src.apps.notification.services.notifications import notification_service
from src.core.dependencies import DB, CurrentActiveSuperuser, get_current_user
from src.core.exceptions import NotFoundError
from src.core.pagination import CursorSortDirection
from src.core.schemas import ApiSuccessResponse, CursorPage, CursorPagination

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "/",
    response_model=CursorPage[NotificationResponse],
    summary="List notifications",
    description="Returns the current user's notifications ordered by recency with cursor pagination.",
)
async def list_notifications(
    db: DB,
    current_user: User = Depends(get_current_user),
    pagination: CursorPagination = Depends(),
    is_read: bool | None = Query(default=None, description="Filter by read state."),
    sort_direction: CursorSortDirection = Query(
        default=CursorSortDirection.DESC,
        description="Sort by newest or oldest notifications.",
    ),
) -> CursorPage[NotificationResponse]:
    return await notification_service.list_notifications(
        db,
        user_id=current_user.id,
        pagination=pagination,
        is_read=is_read,
        sort_direction=sort_direction,
    )


@router.get(
    "/{notification_id}",
    response_model=ApiSuccessResponse[NotificationResponse],
    summary="Get notification",
    description="Fetches a single notification owned by the authenticated user.",
)
async def get_notification(
    notification_id: Annotated[int, Path(description="Notification identifier")],
    db: DB,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[NotificationResponse]:
    notification = await notification_service.get_for_user(db, current_user.id, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found")

    return ApiSuccessResponse(
        message="Notification fetched successfully",
        data=NotificationResponse.model_validate(notification),
    )


@router.patch(
    "/{notification_id}/read",
    response_model=ApiSuccessResponse[NotificationResponse],
    summary="Mark notification as read",
    description="Marks a single notification as read and stores the read timestamp.",
)
async def mark_notification_as_read(
    notification_id: Annotated[int, Path(description="Notification identifier")],
    db: DB,
    current_user: User = Depends(get_current_user),
) -> ApiSuccessResponse[NotificationResponse]:
    notification = await notification_service.mark_as_read(db, notification_id, current_user.id)
    return ApiSuccessResponse(
        message="Notification marked as read",
        data=NotificationResponse.model_validate(notification),
    )


@router.post(
    "/dispatch",
    response_model=ApiSuccessResponse[NotificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch notification",
    description="Creates a notification for the target user and pushes it through realtime, email, or push channels.",
)
async def dispatch_notification(
    data: NotificationCreate,
    db: DB,
    current_user: CurrentActiveSuperuser,
) -> ApiSuccessResponse[NotificationResponse]:
    notification = await notification_service.create_notification(db, data)
    return ApiSuccessResponse(
        message="Notification dispatched successfully",
        data=NotificationResponse.model_validate(notification),
    )
