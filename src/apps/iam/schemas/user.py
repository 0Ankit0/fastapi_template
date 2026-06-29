from typing import Optional, List
from pydantic import  EmailStr, field_serializer, field_validator, model_validator, ValidationInfo
from src.core.enums import RBACRole
from src.core.schemas import BaseSchema
from src.core.types import HashId
from src.core.security import validate_password_strength


class UserBase(BaseSchema):
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    confirm_password: str

    @field_validator("password")
    def validate_password_strength(cls, value):
        validate_password_strength(value)
        return value

    @field_validator("confirm_password")
    def validate_confirm_password(cls, value, info: ValidationInfo):
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value


class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class LoginRequest(BaseSchema):
    organization: Optional[str] = None
    username: str
    password: str


class ResetPasswordRequest(BaseSchema):
    email: EmailStr

class EmailVerificationRequest(BaseSchema):
    email: EmailStr

class ResetPasswordConfirm(BaseSchema):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("confirm_password")
    def validate_confirm_password(cls, value, info: ValidationInfo):
        if "new_password" in info.data and value != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return value

    @field_validator("new_password")
    def validate_password_strength(cls, value):
        validate_password_strength(value)
        return value


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("confirm_password")
    def validate_confirm_password(cls, value, info: ValidationInfo):
        if "new_password" in info.data and value != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return value

    @field_validator("new_password")
    def validate_password_strength(cls, value):
        validate_password_strength(value)
        return value


class VerifyOTPRequest(BaseSchema):
    otp_code: str
    temp_token: str


class DisableOTPRequest(BaseSchema):
    password: str


class UserResponse(BaseSchema):
    id: HashId
    username: str
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    is_confirmed: bool = False
    otp_enabled: bool = False
    otp_verified: bool = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    image_url: Optional[str] = None
    bio: Optional[str] = None
    roles: List[RBACRole] = []


    @model_validator(mode='before')
    @classmethod
    def extract_profile_and_roles(cls, data):
        """Flatten eager-loaded profile and user_roles onto the response dict."""
        if isinstance(data, dict):
            return data
        result = dict(data.__dict__)
        profile = result.get('profile')
        if profile:
            result['first_name'] = profile.first_name or None
            result['last_name'] = profile.last_name or None
            result['phone'] = profile.phone or None
            result['avatar_url'] = profile.avatar_url or None
            result['bio'] = profile.bio or None
        result['roles'] = [
            ur.role.name for ur in (result.get('user_roles') or []) if ur.role
        ]
        return result
