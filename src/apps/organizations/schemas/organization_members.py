from __future__ import annotations
from typing import List

from pydantic import EmailStr

from src.core.enums import RBACRole
from src.core.types import HashId
from src.core.schemas import BaseSchema

class OrganizationMemberBase(BaseSchema):
    user_id: HashId
    organization_id: HashId

class OrganizationMemberCreate(OrganizationMemberBase):
    pass

class OrganizationMembershipInvitationRequest(BaseSchema):
    email: EmailStr
    role: RBACRole

class OrganizationMemberResponse(OrganizationMemberBase):
    id: HashId
    role: List[RBACRole] = []
