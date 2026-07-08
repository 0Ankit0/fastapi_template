from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from src.apps.iam.models.user import User


class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    websocket_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    sse_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    push_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="notification_preference",
    )
