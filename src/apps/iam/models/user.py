from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_confirmed: bool = Field(default=False)
    otp_enabled: bool = Field(default=False)
    otp_verified: bool = Field(default=False)
    otp_base32: str = Field(default="", max_length=255)
    otp_auth_url: str = Field(default="", max_length=255)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Relationships
    profile: Optional["UserProfile"] = Relationship(back_populates="user")


class UserProfileBase(SQLModel):
    first_name: str = Field(default="", max_length=40)
    last_name: str = Field(default="", max_length=40)

class UserProfile(UserProfileBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="profile")
