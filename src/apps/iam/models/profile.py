"""ORM model for user profiles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from . import User
from src.db.base import Base
from src.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from apps.iam.models import User


class UserProfile(Base, TimestampMixin):
    """Represent editable user-facing profile data.

    Profile rows intentionally separate presentation-oriented information from
    the core user account so authentication state and display preferences can
    evolve independently. Each user owns at most one profile row.
    """

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(User.id, ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))
    phone : Mapped[str | None] = mapped_column(String(20))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    bio: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(User, back_populates="profile")
