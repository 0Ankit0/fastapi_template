from __future__ import annotations
from typing import List

from src.core.types import HashId
from src.core.schemas import BaseSchema

class OrganizationMemberBase(BaseSchema):
    user_id: HashId
    organization_id: HashId

class OrganizationMemberCreate(OrganizationMemberBase):
    pass

class OrganizationMemberResponse(OrganizationMemberBase):
    id: HashId
    role: List[str]

    class Config:
        orm_mode = True