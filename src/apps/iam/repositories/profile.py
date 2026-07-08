from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.models import UserProfile
from src.db.query import select


class UserProfileRepository:
    async def create_profile(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        first_name: str = "",
        last_name: str = "",
        phone: str = "",
        avatar_url: str | None = None,
        bio: str | None = None,
    ) -> UserProfile:
        """Create a profile entity linked to a user without committing."""
        profile = UserProfile(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            avatar_url=avatar_url,
            bio=bio,
        )
        db.add(profile)
        return profile

    async def get_profile_by_user_id(self, db: AsyncSession, user_id: int) -> UserProfile | None:
        """Return a user's profile by user id, or None when it does not exist."""
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return result.scalars().first()
