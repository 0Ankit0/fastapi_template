from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base
from sqlalchemy import BigInteger, ForeignKey
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

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="members",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="organization_memberships",
    )