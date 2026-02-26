"""IP access control utility helpers."""
from datetime import datetime
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import and_, select, update

from src.apps.iam.models.ip_access_control import IPAccessControl, IpAccessStatus
from src.apps.iam.models.token_tracking import TokenTracking


def get_client_ip(request: Request) -> str:
    """
    Return the real client IP, preferring forwarded headers set by proxies
    over the direct TCP connection address (which may be 127.0.0.1).
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Header may be a comma-separated list; first entry is the originating client
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def revoke_tokens_for_ip(
    db: AsyncSession,
    user_id: int,
    ip_address: str,
    reason: str = "New token issued for same IP",
) -> None:
    """
    Revoke all active tokens issued to *user_id* from *ip_address*.
    Call this before inserting fresh tokens so stale ones are immediately invalidated.
    Does NOT commit — the caller is responsible for committing the session.
    """
    await db.execute(
        update(TokenTracking)
        .where(and_(
            TokenTracking.user_id == user_id,
            TokenTracking.ip_address == ip_address,
            TokenTracking.is_active == True, 
        ))
        .values(is_active=False, revoked_at=datetime.now(), revoke_reason=reason)
    )


async def upsert_ip_access(
    db: AsyncSession,
    user_id: int,
    ip_address: str,
    status: IpAccessStatus,
    reason: str,
) -> tuple[IPAccessControl, bool]:
    """
    Insert or update the IPAccessControl row for (user_id, ip_address).

    Returns (record, created) where created=True when a new row was added.
    Does NOT commit — the caller is responsible for committing the session.
    """
    result = await db.execute(
        select(IPAccessControl).where(
            IPAccessControl.user_id == user_id,
            IPAccessControl.ip_address == ip_address,
        )
    )
    existing = result.scalars().first()

    if existing:
        existing.status = status
        existing.reason = reason
        existing.last_seen = datetime.now()
        return existing, False

    # Invalidate all other IP entries for this user with same ip before adding the new one.
    await db.execute(
        update(IPAccessControl)
        .where(and_(
            IPAccessControl.user_id == user_id,
            IPAccessControl.ip_address == ip_address,
        ))
        .values(status=IpAccessStatus.BLACKLISTED)
    )

    new_record = IPAccessControl(
        user_id=user_id,
        ip_address=ip_address,
        status=status,
        reason=reason,
        last_seen=datetime.now(),
    )
    db.add(new_record)
    return new_record, True
