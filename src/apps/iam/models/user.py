from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy.orm import  mapped_column, Mapped
from sqlalchemy import BigInteger, DateTime, Boolean, Enum as SQLEnum, String, func, text
from src.db.types import CITEXT_TYPE
from src.core.eums import UserStatus, enum_values
from sqlalchemy.orm import relationship
from datetime import datetime
from src.db.base import Base
from src.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from apps.iam.models import UserProfile, TokenTracking, LoginAttempt, UsedToken
    from apps.organizations.models import Organization, OrganizationMember


class User(Base, TimestampMixin):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    otp_enabled: Mapped[bool] = mapped_column(default=False)
    otp_verified: Mapped[bool] = mapped_column(default=False)
    otp_base32: Mapped[str] = mapped_column(String(255), default="")
    otp_auth_url: Mapped[str] = mapped_column(String(255), default="")    
    email: Mapped[str] = mapped_column(CITEXT_TYPE, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
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

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    created_organizations: Mapped[list["Organization"]] = relationship(
        "Organization",
        back_populates="creator",
        foreign_keys="Organization.created_by",
    )
    owned_organizations: Mapped[list["Organization"]] = relationship(
        "Organization",
        back_populates="owner",
        foreign_keys="Organization.owner_id",
    )
    tokens: Mapped[list["TokenTracking"]] = relationship(
        "TokenTracking",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    login_attempts: Mapped[list["LoginAttempt"]] = relationship(
        "LoginAttempt",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    used_tokens: Mapped[list["UsedToken"]] = relationship(
        "UsedToken",
        back_populates="user",
        cascade="all, delete-orphan",  
    )
    organization_memberships: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="user",
        foreign_keys="OrganizationMember.user_id",
        cascade="all, delete-orphan",
    )