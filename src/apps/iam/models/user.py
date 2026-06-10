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
    from apps.iam.models import TokenTracking
    from apps.organizations.models import Organization

class User(Base, TimestampMixin):

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
    created_organizations: Mapped[list[Organization]] = relationship(
        Organization,
        back_populates="creator",
        foreign_keys="Organization.created_by",
    )
    owned_organizations: Mapped[list[Organization]] = relationship(
        Organization,
        back_populates="owner",
        foreign_keys="Organization.owner_id",
    )
    tokens: Mapped[list[TokenTracking]] = relationship(
        "TokenTracking",
        back_populates="user",
        cascade="all, delete-orphan",
    )