from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.apps.iam.models import User, UserProfile
from src.core.enums import UserStatus
from src.db.query import func, or_, select


class UserRepository:
    async def get_user_by_username(self, db: AsyncSession, username: str) -> User | None:
        """Return the first user that matches the provided username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalars().first()

    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Return the first user that matches the provided email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        """Return a user by primary key, or None when not found."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_user_with_profile(self, db: AsyncSession, user_id: int) -> User | None:
        """Return a user with the related profile eagerly loaded."""
        result = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == user_id)
        )
        return result.scalars().first()

    async def list_users_with_profile(
        self,
        db: AsyncSession,
        *,
        search: str | None,
        is_active: bool | None,
        cursor_id: int | None,
        limit: int,
        sort_desc: bool,
    ) -> Sequence[User]:
        """Return a cursor-paginated user list with optional search and active filters."""
        query = select(User).options(selectinload(User.profile))

        if search:
            query = query.where(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                )
            )

        if is_active is not None:
            if is_active:
                query = query.where(User.status == UserStatus.ACTIVE)
            else:
                query = query.where(User.status != UserStatus.ACTIVE)

        if cursor_id is not None:
            if sort_desc:
                query = query.where(User.id < cursor_id)
            else:
                query = query.where(User.id > cursor_id)

        if sort_desc:
            query = query.order_by(User.id.desc())
        else:
            query = query.order_by(User.id.asc())

        query = query.limit(limit + 1)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_user_email_in_use(self, db: AsyncSession, email: str, exclude_user_id: int) -> User | None:
        """Return a user that already owns an email, excluding the given user id."""
        result = await db.execute(
            select(User).where(
                User.email == email,
                User.id != exclude_user_id,
            )
        )
        return result.scalars().first()

    async def create_user(self, db: AsyncSession, *, username: str, email: str, password_hash: str) -> User:
        """Create and flush a new user row, returning the ORM entity."""
        user = User(username=username, email=email, password_hash=password_hash)
        db.add(user)
        await db.flush()
        return user

    async def get_active_users_count(self, db: AsyncSession, user_ids: list[int]) -> int:
        """Count active users for the provided user id set."""
        if not user_ids:
            return 0
        return (
            await db.execute(
                select(func.count(User.id)).where(
                    User.id.in_(user_ids),
                    User.status == UserStatus.ACTIVE,
                )
            )
        ).scalar_one() or 0

    async def get_superusers_count(self, db: AsyncSession, user_ids: list[int]) -> int:
        """Count superusers for the provided user id set."""
        if not user_ids:
            return 0
        return (
            await db.execute(
                select(func.count(User.id)).where(
                    User.id.in_(user_ids),
                    User.is_superuser.is_(True),
                )
            )
        ).scalar_one() or 0

    async def delete_user(self, db: AsyncSession, user: User) -> None:
        """Mark a user entity for deletion in the current transaction."""
        await db.delete(user)

    async def upsert_user_avatar(self, db: AsyncSession, *, user: User, avatar_url: str) -> User:
        """Create or update a user's profile avatar and persist the change."""
        if user.profile:
            user.profile.avatar_url = avatar_url
            db.add(user.profile)
        else:
            profile = UserProfile(user_id=user.id, avatar_url=avatar_url)
            db.add(profile)
            user.profile = profile

        await db.commit()
        await db.refresh(user)
        if user.profile:
            await db.refresh(user.profile)
        return user

    async def update_current_user_fields(
        self,
        db: AsyncSession,
        *,
        user: User,
        email: str | None,
        first_name: str | None,
        last_name: str | None,
        phone: str | None,
    ) -> User:
        """Update the current user's mutable fields and profile values, then commit."""
        if email is not None:
            user.email = email
            user.is_confirmed = False

        if user.profile:
            if first_name is not None:
                user.profile.first_name = first_name
            if last_name is not None:
                user.profile.last_name = last_name
            if phone is not None:
                user.profile.phone = phone

        db.add(user)
        await db.commit()
        await db.refresh(user)
        if user.profile:
            await db.refresh(user.profile)
        return user

    async def update_user_with_profile_fields(
        self,
        db: AsyncSession,
        *,
        user: User,
        email: str | None,
        first_name: str | None,
        last_name: str | None,
        phone: str | None,
    ) -> User:
        """Update an arbitrary user and upsert profile fields in one transaction."""
        if email is not None:
            user.email = email

        profile = await self.get_profile_by_user_id(db, user.id)
        if profile:
            if first_name is not None:
                profile.first_name = first_name
            if last_name is not None:
                profile.last_name = last_name
            if phone is not None:
                profile.phone = phone
            db.add(profile)
        elif any(value is not None for value in [first_name, last_name, phone]):
            profile = UserProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
            )
            db.add(profile)

        db.add(user)
        await db.commit()
        if profile:
            await db.refresh(profile)
            user.profile = profile
        return user
