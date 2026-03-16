from typing import List, Optional
import strawberry
from src.apps.iam.models.user import User

@strawberry.type
class UserType:
    id: int
    username: str
    email: str
    is_active: bool
    is_superuser: bool
    is_confirmed: bool
    otp_enabled: bool
    otp_verified: bool
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    image_url: Optional[str]
    bio: Optional[str]
    roles: List[str]

    @staticmethod
    def from_orm(user: User) -> "UserType":
        profile = user.profile
        return UserType(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_confirmed=user.is_confirmed,
            otp_enabled=user.otp_enabled,
            otp_verified=user.otp_verified,
            first_name=profile.first_name if profile else None,
            last_name=profile.last_name if profile else None,
            phone=profile.phone if profile else None,
            image_url=profile.image_url if profile else None,
            bio=profile.bio if profile else None,
            roles=[],
        )

@strawberry.input
class UserUpdateInput:
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
