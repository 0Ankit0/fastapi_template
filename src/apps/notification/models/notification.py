from __future__ import annotations

from enum import Enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.enums import enum_values
from src.db.base import Base
from src.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from src.apps.iam.models.user import User


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[NotificationType] = mapped_column(
        SQLEnum(
            NotificationType,
            name="notification_type",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
        default=NotificationType.INFO,
        server_default=NotificationType.INFO.value,
        index=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        index=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
    )

    __table_args__ = (
        Index("ix_notifications_user_created_at", "user_id", "created_at"),
    )
