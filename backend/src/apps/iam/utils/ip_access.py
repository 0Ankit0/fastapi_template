"""IP access control utility helpers."""
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.apps.iam.models.ip_access_control import IPAccessControl, IpAccessStatus


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

    new_record = IPAccessControl(
        user_id=user_id,
        ip_address=ip_address,
        status=status,
        reason=reason,
        last_seen=datetime.now(),
    )
    db.add(new_record)
    return new_record, True
