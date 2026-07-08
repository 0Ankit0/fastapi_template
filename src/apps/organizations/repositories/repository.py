from __future__ import annotations

from .invitation_tracking import InvitationTrackingRepository
from .organization import OrganizationModelRepository
from .organization_member import OrganizationMemberRepository


class OrganizationRepository(
    OrganizationModelRepository,
    OrganizationMemberRepository,
    InvitationTrackingRepository,
):
    pass


organization_repository = OrganizationRepository()
