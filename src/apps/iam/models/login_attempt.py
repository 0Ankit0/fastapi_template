from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from .user import User



class LoginAttempt(Base):
    __tablename__ = "loginattempt"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, default=None, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        default=None,
    )
    ip_address: Mapped[str] = mapped_column(String(45))
    user_agent: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    attempted_username: Mapped[str] = mapped_column(String(150), default="")
    success: Mapped[bool] = mapped_column(default=False)
    failure_reason: Mapped[str] = mapped_column(String(255), default="")

    user: Mapped["User | None"] = relationship(
        back_populates="login_attempts",
        passive_deletes=True,
    )
        