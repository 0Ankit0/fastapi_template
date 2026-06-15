from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.types import JSONB_TYPE
from src.core.eums import OrganizationMemberStatus, enum_values
from src.db.base import Base
from sqlalchemy import BigInteger, DateTime, ForeignKey,Enum as SQLEnum, Index, UniqueConstraint
from src.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from iam.models import User
    from .organization import Organization

class OrganizationMember(Base, TimestampMixin):
    """Represents a user's membership in an organization"""

    __tablename__ = "organization_members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[OrganizationMemberStatus] = mapped_column(
        SQLEnum(
            OrganizationMemberStatus,
            name="organization_member_status",
            native_enum=False,
            values_callable = enum_values,
        ), 
        default=OrganizationMemberStatus.INVITED, 
        server_default=OrganizationMemberStatus.INVITED.value,
        nullable=False
    )
    invited_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extra_metadata: Mapped[dict | None] = mapped_column(JSONB_TYPE)

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="organization_memberships",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_user"),
        # Index("idx_organization_member_organization_id_status", "organization_id", "status"),
    )