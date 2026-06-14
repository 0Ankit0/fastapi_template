

from typing_extensions import Annotated

from fastapi import Depends, Request

from src.apps.iam.dependencies import get_current_user
from src.apps.iam.models.user import User
from src.core.dependencies import DB
from src.apps.organizations.models import Organization
from src.core.security import decode_token
from src.db.session import get_session

CurrentUser = Annotated[User, Depends(get_current_user)]
# TODO: get the curernt org from paseto token payload
async def get_current_org(
    request: Request,
    db: DB,
    current_user: CurrentUser = Depends(get_current_user),
) -> Organization | None:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    org_slug = decode_token(token).get("org")
    if not org_slug:
        raise ValueError("Organization slug not found in token")
    ...