from typing import Optional, List
from sqlmodel import SQLModel
from pydantic import validator

class UserBase(SQLModel):
    email: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(SQLModel):
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

from typing import List

class UserRead(SQLModel):
    id: str
    email: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    roles: List[str] = []
    avatar: Optional[str] = None
    
    @validator("id", pre=True)
    def id_to_string(cls, v):
        return str(v)
