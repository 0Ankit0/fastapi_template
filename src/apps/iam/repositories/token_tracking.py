from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.models import LoginAttempt
from src.apps.iam.models.token_tracking import TokenTracking
from src.db.query import func, select


class TokenTrackingRepository:
    async def create_token_tracking(self, db: AsyncSession, **kwargs) -> TokenTracking:
        """Create a token tracking entity without committing."""
        token_tracking = TokenTracking(**kwargs)
        db.add(token_tracking)
        return token_tracking

    async def get_active_refresh_tracking_by_jti(self, db: AsyncSession, token_jti: str) -> TokenTracking | None:
        """Return an active refresh-token tracking record by JTI."""
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.token_jti == token_jti,
                TokenTracking.is_active,
            )
        )
        return result.scalars().first()

    async def get_token_tracking_by_id(self, db: AsyncSession, token_id: int, user_id: int) -> TokenTracking | None:
        """Return a tracked token by id for a specific user."""
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.id == token_id,
                TokenTracking.user_id == user_id,
            )
        )
        return result.scalars().first()

    async def list_active_tokens(self, db: AsyncSession, user_id: int):
        """List all active tracked tokens for a user."""
        result = await db.execute(
            select(TokenTracking).where(
                TokenTracking.user_id == user_id,
                TokenTracking.is_active,
            )
        )
        return result.scalars().all()

    async def list_active_tokens_paginated(
        self,
        db: AsyncSession,
        user_id: int,
        query_filter_fn,
        query_order_fn,
        limit: int,
    ) -> Sequence[TokenTracking]:
        """List active tokens for a user with caller-provided pagination clauses."""
        query = select(TokenTracking).where(
            TokenTracking.user_id == user_id,
            TokenTracking.is_active,
        )
        query = query_filter_fn(query)
        query = query_order_fn(query).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def count_tokens(self, db: AsyncSession, *, user_id: int, is_active: bool | None = None, expires_before=None, expires_after=None) -> int:
        """Count user tokens using optional active/expiration filters."""
        query = select(func.count(TokenTracking.id)).where(TokenTracking.user_id == user_id)
        if is_active is not None:
            query = query.where(TokenTracking.is_active.is_(is_active))
        if expires_before is not None:
            query = query.where(TokenTracking.expires_at <= expires_before)
        if expires_after is not None:
            query = query.where(TokenTracking.expires_at >= expires_after)
        return (await db.execute(query)).scalar_one() or 0

    async def get_user_token_counts(self, db: AsyncSession, user_id: int) -> dict[str, int]:
        """Return aggregate active and revoked token counts for a user."""
        active = await self.count_tokens(db, user_id=user_id, is_active=True)
        revoked = await self.count_tokens(db, user_id=user_id, is_active=False)
        return {"active": int(active), "revoked": int(revoked)}

    async def revoke_tokens(self, db: AsyncSession, *, tokens: Sequence[TokenTracking], reason: str) -> int:
        """Revoke multiple tracked tokens and persist the revocation reason."""
        for token_tracking in tokens:
            token_tracking.is_active = False
            token_tracking.revoked_at = datetime.now(timezone.utc)
            token_tracking.revoke_reason = reason
        await db.commit()
        return len(tokens)

    async def revoke_token(self, db: AsyncSession, *, token_tracking: TokenTracking, reason: str) -> None:
        """Revoke a single tracked token with a reason and commit."""
        token_tracking.is_active = False
        token_tracking.revoked_at = datetime.now(timezone.utc)
        token_tracking.revoke_reason = reason
        await db.commit()
