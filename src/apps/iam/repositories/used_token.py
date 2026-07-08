from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.models import UsedToken
from src.db.query import select


class UsedTokenRepository:
    async def get_used_token_by_jti(self, db: AsyncSession, token_jti: str) -> UsedToken | None:
        """Return a used-token record by JTI, or None if unused."""
        result = await db.execute(select(UsedToken).where(UsedToken.token_jti == token_jti))
        return result.scalars().first()

    async def mark_used_token(self, db: AsyncSession, *, token_jti: str, user_id: int, purpose: str) -> UsedToken:
        """Create a used-token marker to prevent token replay."""
        used_token = UsedToken(token_jti=token_jti, user_id=user_id, token_purpose=purpose)
        db.add(used_token)
        return used_token
