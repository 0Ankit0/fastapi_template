from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from app.models.user import User

class TenantRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"

class TenantType(str, Enum):
    DEFAULT = "default"
    ORGANIZATION = "organization"

class TenantMembershipBase(SQLModel):
    is_accepted: bool = False
    invitation_accepted_at: Optional[datetime] = None
    role: TenantRole = TenantRole.OWNER 
    invitee_email_address: Optional[str] = None

class TenantMembership(TenantMembershipBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenant.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    tenant: "Tenant" = Relationship(back_populates="memberships")
    user: "User" = Relationship() 

class TenantBase(SQLModel):
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    type: TenantType = TenantType.DEFAULT
    billing_email: Optional[str] = None

class Tenant(TenantBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    memberships: List["TenantMembership"] = Relationship(back_populates="tenant")
