from alembic.util import status
from fastapi import Depends, HTTPException

from apps.iam.models.user import User
from core.dependencies import DB
from db.session import get_db
from .casbin import enforcer
from fastapi import Request
from fastapi import status 

#TODO: get the curernt user from paseto token payload 
async def get_current_user(db: DB = Depends(get_db)) -> User:
    ...

def require_permission(module: str, action: str):
    async def checker(request: Request):
        # TODO: Extract user and org info from token payload
        payload = request.state.token_payload

        user_id = payload["sub"]
        org_id = payload["organization_id"]

        allowed = enforcer.enforce(
            user_id,
            org_id,
            module,
            action,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    return Depends(checker)