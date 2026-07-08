from __future__ import annotations

from fastapi import APIRouter, Query, Request, status
from src.core.dependencies import DB
from src.core.schemas import ApiSuccessResponse
from src.core.logging import get_logger
import src.core.security as security
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.apps.organizations.services.organization_members import organization_members_service

logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(
    prefix="/organizations/members",
    tags=["Organization Members"],
)
PUBLIC_ORG_MEMBERS_RATE_LIMIT = limiter.limit("10/minute")

@router.get(
    "/accept-invitation/",
    name="accept_invitation",
    status_code=status.HTTP_200_OK,
    response_model=ApiSuccessResponse[None],
    summary="Accept organization invitation",
    description="Validates a secure invitation token and activates the pending organization membership.",
)
@PUBLIC_ORG_MEMBERS_RATE_LIMIT
async def accept_invitation(
    db: DB,
    request: Request,
    t: str = Query(..., description="Invitation token to verify"),
) ->  ApiSuccessResponse[None]:
    """
    Verify the validity of an organization membership invitation token.
    """
    return await organization_members_service.accept_invitation(db, token=t)
