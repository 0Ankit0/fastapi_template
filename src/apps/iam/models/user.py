from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import BigInteger, DateTime, Boolean, Enum as SQLEnum, func, text
from db.types import CITEXT_TYPE
from core.eums import UserStatus, enum_values
from sqlalchemy.orm import relationship
from datetime import datetime
from db.base import Base
from db.mixins import TimestampMixin

if TYPE_CHECKING:
    from apps.iam.models import Profile

class User(Base, TimestampMixin):
    """Represent a platform user account.

    The user row is the root identity entity for authentication, profile data,
    linked identities, memberships, sessions, and security logs. Related tables
    hold specialized state so the core account record stays stable and compact.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(CITEXT_TYPE, unique=True, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(
            UserStatus,
            name="user_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
        index=True,
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[Profile | None] = relationship(
        Profile,
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )