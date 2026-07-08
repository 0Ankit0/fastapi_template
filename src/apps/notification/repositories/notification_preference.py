from __future__ import annotations

from sqlalchemy import select

from src.apps.notification.models.notification_preference import NotificationPreference


class NotificationPreferenceRepository:
    async def get_preference(self, db, user_id: int) -> NotificationPreference | None:
        """Return notification preferences for a user, if configured."""
        result = await db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return result.scalars().first()

    async def create_preference(self, db, user_id: int) -> NotificationPreference:
        """Create default notification preferences for a user and commit."""
        preference = NotificationPreference(user_id=user_id)
        db.add(preference)
        await db.commit()
        await db.refresh(preference)
        return preference

    async def update_preference_and_commit(self, db, *, preference: NotificationPreference, updates: dict) -> NotificationPreference:
        """Apply preference field updates and commit the modified entity."""
        for field_name, value in updates.items():
            setattr(preference, field_name, value)
        db.add(preference)
        await db.commit()
        await db.refresh(preference)
        return preference
