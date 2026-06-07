

from fastapi import Depends

from apps.iam.dependencies import get_current_user
from core.dependencies import DB, CurrentUser
from apps.organizations.models import Organization
from db.session import get_db

# TODO: get the curernt org from paseto token payload
async def get_current_org(
    db: DB = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Organization:
    ...