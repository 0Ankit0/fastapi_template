from typing import Optional, List
from pydantic import  EmailStr, field_serializer, field_validator, model_validator, ValidationInfo, ConfigDict
from src.core.enums import RBACRole
from src.core.schemas import BaseSchema
from src.core.types import HashId
from src.core.security import validate_password_strength


class UserBase(BaseSchema):
    username: str
    email: EmailStr
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


class LoginRequest(BaseSchema):
    model_config = ConfigDict(extra="forbid")
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
        profile = getattr(data, "profile", None)
        user_roles = getattr(data, "user_roles", []) or []
        status = getattr(data, "status", None)
        result = {
            "id": getattr(data, "id", None),
            "username": getattr(data, "username", None),
            "email": getattr(data, "email", None),
            "is_active": getattr(status, "value", status) == "active",
            "is_superuser": getattr(data, "is_superuser", False),
            "is_confirmed": getattr(data, "is_confirmed", False),
            "otp_enabled": getattr(data, "otp_enabled", False),
            "otp_verified": getattr(data, "otp_verified", False),
        }
        if profile:
            result["first_name"] = getattr(profile, "first_name", None) or None
            result["last_name"] = getattr(profile, "last_name", None) or None
            result["phone"] = getattr(profile, "phone", None) or None
            result["image_url"] = getattr(profile, "avatar_url", None) or None
            result["bio"] = getattr(profile, "bio", None) or None
        result["roles"] = [
            getattr(getattr(ur, "role", None), "name", None)
            for ur in user_roles
            if getattr(ur, "role", None)
        ]
        return result
