from typing import Optional, List
from sqlmodel import SQLModel
from pydantic import EmailStr, field_serializer, field_validator, ValidationInfo
from ..utils.hashid import encode_id

class UserBase(SQLModel):
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
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit")
        return value

    @field_validator("confirm_password")
    def validate_confirm_password(cls, value, info: ValidationInfo):
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value

class UserUpdate(SQLModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class LoginRequest(SQLModel):
    username: str
    password: str

class ResetPasswordRequest(SQLModel):
    email: EmailStr

class ResetPasswordConfirm(SQLModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("confirm_password")
    def validate_confirm_password(cls, value, info: ValidationInfo):
        if "new_password" in info.data and value != info.data["new_password"]:
            raise ValueError("Passwords do not match")
        return value

class ChangePasswordRequest(SQLModel):
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
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit")
        return value

class VerifyOTPRequest(SQLModel):
    otp_code: str

class DisableOTPRequest(SQLModel):
    password: str
    
class UserResponse(UserBase):
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    roles: List[str] = []

    @field_serializer("id")
    def serialize_id(self, value: int) -> str:
        return encode_id(value)
    
   