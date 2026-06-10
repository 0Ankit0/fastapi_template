from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from .user import User



class UsedToken( Base):
    __tablename__ = "usedtoken"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, default=None, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        default=None,
    )
    token_jti: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    token_purpose: Mapped[str] = mapped_column(String(50))
    used_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User | None"] = relationship(back_populates="used_tokens", passive_deletes=True)