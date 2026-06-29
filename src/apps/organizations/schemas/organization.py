from __future__ import annotations

from src.core.types import HashId
from src.core.schemas import BaseSchema
from src.core.enums import OrganizationStatus

class OrganizationBase(BaseSchema):
    name: str
    description: str | None = None


class OrganizationCreate(OrganizationBase):
    slug: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE

class OrganizationUpdate(OrganizationBase):
    status: OrganizationStatus | None = None
    pass

class OrganizationPartialUpdate(BaseSchema):
    status: OrganizationStatus


class OrganizationResponse(OrganizationBase):
    id: HashId
    slug: str
    status: OrganizationStatus


