from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column, relationship
from src.db.mixins import CreatedAtMixin
from src.core.security import TokenType
from src.db.base import Base

if TYPE_CHECKING:
    from .user import User


class TokenTracking(Base, CreatedAtMixin):
    __tablename__ = "tokentracking"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        default=None,
    )
    token_jti: Mapped[str] = mapped_column(String(255), index=True, unique=True, doc="Unique identifier for the token (jti claim)")
    token_type: Mapped[TokenType] = mapped_column(
        SAEnum(
            TokenType,
            values_callable=lambda enum_cls: [member.name for member in enum_cls],
            name="tokentype",
        )
    )
    ip_address: Mapped[str] = mapped_column(String(45), doc="IP address of the client that requested the token")
    user_agent: Mapped[str] = mapped_column(String(255), doc="User agent string of the client that requested the token")
    expires_at: Mapped[datetime] = mapped_column(doc="Timestamp when the token expires")
    is_active: Mapped[bool] = mapped_column(default=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(doc="Timestamp when the token was revoked", default=None)
    revoke_reason: Mapped[str] = mapped_column(String(255), doc="Reason for revoking the token", default="")
    user: Mapped["User | None"] = relationship(back_populates="tokens")