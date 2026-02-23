from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from .login_attempt import LoginAttempt
    from .ip_access_control import IPAccessControl
    from .token_tracking import TokenTracking
    from .used_token import UsedToken
    from .role import UserRole

class UserBase(SQLModel):
    username: str = Field(
        unique=True,
        index=True,
        max_length=50,
        description="Unique username for the user"
    )
    email: str = Field(
        unique=True,
        index=True,
        max_length=255,
        regex=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        description="User's email address"
    )
    is_active: bool = Field(
        default=True,
        description="Indicates whether the user account is active"
    )
    is_superuser: bool = Field(
        default=False,
        description="Indicates whether the user has superuser privileges"
    )
    is_confirmed: bool = Field(
        default=False,
        description="Indicates whether the user's email is confirmed"
    )
    otp_enabled: bool = Field(
        default=False,
        description="Indicates whether OTP is enabled for the user"
    )
    otp_verified: bool = Field(
        default=False,
        description="Indicates whether OTP is verified for the user"
    )
    otp_base32: str = Field(
        default="",
        max_length=255,
        description="Base32 encoded OTP secret key for the user"
    )
    otp_auth_url: str = Field(
        default="",
        max_length=255,
        description="OTP authentication URL for the user"
    )

class User(UserBase, table=True):
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    hashed_password: str = Field(
        max_length=255,
        description="Hashed password for the user"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the user was created"
    )
    
    # Relationships
    profile: Optional["UserProfile"] = Relationship(back_populates="user")
    login_attempts: list["LoginAttempt"] = Relationship(back_populates="user")
    ip_access_controls: list["IPAccessControl"] = Relationship(back_populates="user")
    tokens: list["TokenTracking"] = Relationship(back_populates="user")
    used_tokens: list["UsedToken"] = Relationship(back_populates="user")
    user_roles: list["UserRole"] = Relationship(back_populates="user")


class UserProfileBase(SQLModel):
    first_name: str = Field(
        default="",
        max_length=40,
        description="User's first name"
    )
    last_name: str = Field(
        default="",
        max_length=40,
        description="User's last name"
    )
    phone: str = Field(
        default="",
        max_length=20,
        regex=r'^\+?[1-9]\d{1,14}$',
        description="User's phone number"
    )
    image_url: str = Field(
        default="",
        max_length=255,
        description="URL to the user's profile image"
    )
    bio: str = Field(
        default="",
        max_length=500,
        description="Short biography or description of the user"
    )

class UserProfile(UserProfileBase, table=True):
    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )
    user_id: Optional[int] = Field(
        default=None,
        foreign_key="user.id"
    )

    # Relationships
    user: Optional[User] = Relationship(back_populates="profile")
