from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.apps.organizations.models.organization_members import OrganizationMember
from src.db.base import Base
from sqlalchemy import BigInteger, Text, ForeignKey, Enum as SQLEnum
from src.db.types import CITEXT_TYPE
from src.db.mixins import TimestampMixin
from src.core.enums import OrganizationStatus, enum_values

if TYPE_CHECKING:
    from iam.models import User
    from . import OrganizationMember

class Organization(Base, TimestampMixin):
    """Represent a tenant organization within the shared application database.

    The organization row anchors membership, settings, project attachments,
    audit history, and outbox events for a single tenant boundary. Related rows
    provide the operational and authorization state that hangs off this core
    entity.
    """

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(CITEXT_TYPE, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OrganizationStatus] = mapped_column(
        SQLEnum(
            OrganizationStatus,
            name="organization_status",
            native_enum=False,
            values_callable=enum_values,
        ),
        nullable=False,
        default=OrganizationStatus.ACTIVE,
        server_default=OrganizationStatus.ACTIVE.value,
        index=True,
    )
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    billing_email: Mapped[str | None] = mapped_column(CITEXT_TYPE)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    creator: Mapped["User"] = relationship(
        "User",
        back_populates="created_organizations",
        foreign_keys=[created_by],
    )
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_organizations",
        foreign_keys=[owner_id],
    )
    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
    )