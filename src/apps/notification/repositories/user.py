from __future__ import annotations

from sqlalchemy import select

from src.apps.iam.models.user import User


class NotificationUserRepository:
    async def get_user(self, db, user_id: int) -> User | None:
        """Return a user entity used for notification delivery metadata."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()
