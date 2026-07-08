from __future__ import annotations

from .notification import NotificationModelRepository
from .notification_preference import NotificationPreferenceRepository
from .user import NotificationUserRepository


class NotificationRepository(
    NotificationModelRepository,
    NotificationPreferenceRepository,
    NotificationUserRepository,
):
    pass


notification_repository = NotificationRepository()
