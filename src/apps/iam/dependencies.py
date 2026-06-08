from alembic.util import status
from fastapi import Depends, HTTPException

from apps.iam.models.user import User
from core.dependencies import DB
from db.session import get_db
from .casbin import enforcer
from fastapi import Request
from fastapi import status 
from src.core.eums import RBACAction as Action, RBACModule as Module

METHOD_ACTION_MAP = {
    "GET": Action.READ,
    "POST": Action.CREATE,
    "PUT": Action.UPDATE,
    "PATCH": Action.UPDATE,
    "DELETE": Action.DELETE,
}

#TODO: get the curernt user from paseto token payload 
async def get_current_user(db: DB = Depends(get_db)) -> User:
    ...

def require_module_permission(module: Module):
    async def checker(request: Request):
        # TODO: Extract user and org info from token payload
        payload = request.state.token_payload

        user_id = payload["sub"]
        org_id = payload["organization_id"]

        action = METHOD_ACTION_MAP[request.method]

        allowed = enforcer.enforce(
            user_id,
            org_id,
            module.value,
            action.value,
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

    return Depends(checker)