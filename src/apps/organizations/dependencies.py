

from fastapi import Depends, Request

from apps.iam.dependencies import get_current_user
from core.dependencies import DB, CurrentUser
from apps.organizations.models import Organization
from core.security import decode_token
from db.session import get_session

# TODO: get the curernt org from paseto token payload
async def get_current_org(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: DB = Depends(get_session),
) -> Organization | None:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    org_slug = decode_token(token).get("org")
    if not org_slug:
        raise ValueError("Organization slug not found in token")
    ...