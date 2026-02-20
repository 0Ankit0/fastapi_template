from typing import Optional,List
from sqlmodel import SQLModel
from pydantic import EmailStr, EmailStr, field_serializer,field_validator
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

    @field_validator("confirm_password")
    def validate_confirm_password(cls, value, values):
        if "password" in values and value != values["password"]:
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

class ResetPasswordRequest(SQLModel):
    email: EmailStr

class ResetPasswordConfirm(SQLModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("confirm_password")
    def validate_confirm_password(cls, value, values):
        if "new_password" in values and value != values["new_password"]:
            raise ValueError("Passwords do not match")
        return value
    
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
    
   