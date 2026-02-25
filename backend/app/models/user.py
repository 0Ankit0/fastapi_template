from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    is_confirmed: bool = False
    otp_enabled: bool = False
    otp_verified: bool = False
    otp_base32: str = Field(default="", max_length=255)
    otp_auth_url: str = Field(default="", max_length=255)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    profile: Optional["UserProfile"] = Relationship(back_populates="user")


class UserProfileBase(SQLModel):
    first_name: str = Field(default="", max_length=40)
    last_name: str = Field(default="", max_length=40)

class UserProfile(UserProfileBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="profile")
