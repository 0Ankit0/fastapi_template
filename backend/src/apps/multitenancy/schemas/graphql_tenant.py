import strawberry
from typing import List, Optional

from src.apps.multitenancy.schemas.tenant import (
    TenantResponse,
    TenantWithMembersResponse,
    TenantMemberResponse,
    TenantInvitationResponse,
)


@strawberry.experimental.pydantic.type(model=TenantResponse, all_fields=True)
class TenantType:
    """GraphQL representation of a tenant."""


@strawberry.experimental.pydantic.type(model=TenantMemberResponse, all_fields=True)
class TenantMemberType:
    """GraphQL representation of a tenant member."""


@strawberry.experimental.pydantic.type(model=TenantWithMembersResponse, all_fields=True)
class TenantWithMembersType:
    """GraphQL representation of a tenant including member list."""


@strawberry.experimental.pydantic.type(model=TenantInvitationResponse, all_fields=True)
class TenantInvitationType:
    """GraphQL representation of a tenant invitation."""
