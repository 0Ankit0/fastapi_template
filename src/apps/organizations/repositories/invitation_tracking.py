from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.models.token_tracking import TokenTracking
from src.apps.iam.models.user import User
from src.core.security import TokenType
from src.db.query import select


class InvitationTrackingRepository:
    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Return a user by email for invitation workflows."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> User | None:
        """Return a user by id for invitation workflows."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_invitation_tracking(self, db: AsyncSession, *, user_id: int | None, request_user_agent: str | None, ip_address: str | None) -> TokenTracking:
        """Create invitation token tracking metadata without committing."""
        tracking = TokenTracking(
            user_id=user_id,
            token_jti=str(uuid4()),
            user_agent=request_user_agent or "",
            ip_address=ip_address,
            token_type=TokenType.ORGANIZATION_INVITATION.value,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        db.add(tracking)
        return tracking

    async def create_invitation_tracking_and_commit(
        self,
        db: AsyncSession,
        *,
        user_id: int | None,
        request_user_agent: str | None,
        ip_address: str | None,
    ) -> TokenTracking:
        """Create and commit invitation tracking metadata."""
        tracking = await self.create_invitation_tracking(
            db,
            user_id=user_id,
            request_user_agent=request_user_agent,
            ip_address=ip_address,
        )
        await db.commit()
        return tracking
