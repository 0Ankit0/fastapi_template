from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.models import LoginAttempt
from src.db.query import select


class LoginAttemptRepository:
    async def create_login_attempt(self, db: AsyncSession, **kwargs: Any) -> LoginAttempt:
        """Create a login attempt record without committing."""
        login_attempt = LoginAttempt(**kwargs)
        db.add(login_attempt)
        return login_attempt

    async def get_login_failures(self, db: AsyncSession, *, user_id: int, window_start: datetime) -> Sequence[LoginAttempt]:
        """Return failed login attempts for a user within a time window."""
        result = await db.execute(
            select(LoginAttempt)
            .where(
                LoginAttempt.user_id == user_id,
                LoginAttempt.success == False,
                LoginAttempt.timestamp >= window_start,
            )
            .order_by(LoginAttempt.timestamp.desc())
        )
        return result.scalars().all()

    async def get_login_attempts_in_window(self, db: AsyncSession, *, attempted_username: str, window_start: datetime) -> Sequence[LoginAttempt]:
        """Return login attempts for a username within a time window."""
        result = await db.execute(
            select(LoginAttempt).where(
                LoginAttempt.attempted_username == attempted_username,
                LoginAttempt.timestamp >= window_start,
            )
        )
        return result.scalars().all()
