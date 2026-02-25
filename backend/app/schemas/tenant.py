from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel

class TenantBase(SQLModel):
    name: str
    slug: Optional[str] = None
    type: Optional[str] = "default"

class TenantCreate(TenantBase):
    pass

class TenantRead(TenantBase):
    id: int
    created_at: datetime
    owners_count: int = 1 # Simplified for now

class TenantUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[str] = None
