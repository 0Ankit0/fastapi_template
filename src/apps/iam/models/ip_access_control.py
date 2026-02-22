from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from .user import User


class IPAccessControlBase(SQLModel):
    ip_address: str = Field(
        max_length=45,
        index=True,
        description="IP address for access control"
    )
    status: str = Field(
        max_length=20,
        default="pending",
        description="Status: pending, whitelisted, blacklisted"
    )
    reason: str = Field(
        default="",
        max_length=255,
        description="Reason for blacklisting or note"
    )
    last_seen: datetime = Field(
        default_factory=datetime.now,
        description="Last time this IP attempted access"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When this IP was first recorded"
    )


class IPAccessControl(IPAccessControlBase, table=True):
    id: int = Field(
        default=None,
        primary_key=True,
        description="Unique identifier for the IP access control entry"
    )
    user_id: int = Field(
        foreign_key="user.id",
        ondelete="CASCADE",
        description="ID of the user this IP access control belongs to"
    )

    # Relationships
    user: Optional[User] = Relationship(back_populates="ip_access_controls")
