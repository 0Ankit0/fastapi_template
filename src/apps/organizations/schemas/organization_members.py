from __future__ import annotations
from typing import List

from src.core.eums import RBACRole
from src.core.types import HashId
from src.core.schemas import BaseSchema

class OrganizationMemberBase(BaseSchema):
    user_id: HashId
    organization_id: HashId

class OrganizationMemberCreate(OrganizationMemberBase):
    pass

class OrganizationMembershipInvitationRequest(BaseSchema):
    organization_id: HashId
    member_id: HashId
    role: RBACRole

class OrganizationMemberResponse(OrganizationMemberBase):
    id: HashId
    role: RBACRole
