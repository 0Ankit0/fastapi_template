from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from src.apps.organizations.models.organization import Organization
from src.apps.iam.models import User
from src.apps.iam.services.policy_service import PolicyService
from src.core.eums import RBACModule as Module
from src.core.dependencies import (
    DB,
    get_current_org,
    get_current_active_superuser,
    require_module_permission,
)
from src.core.logging import get_logger
from src.core.exceptions import NotFoundError, ConflictError
from src.core.schemas import ApiSuccessResponse
from src.core.types import (
    HashId,
)
from src.apps.iam.schemas.casbin import (
    PermissionRequest,
    PermissionResponse,
    RoleResponse,
    UserRoleRequest,
    RoleInheritanceRequest,
    PermissionCheckRequest,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
CurrentOrg = Annotated[Organization, Depends(get_current_org)]
CurrentUser = Annotated[User, Depends(get_current_active_superuser)]

router = APIRouter(
    prefix="/organizations/{org}/rbac",
    tags=["RBAC"],
    dependencies=[
        Depends(require_module_permission(Module.RBAC)),
        # Depends(get_current_active_superuser)
    ]
)

logger = get_logger(__name__)

CASBIN_RATE_LIMIT = limiter.limit("10/minute")
AUTHORIZATION_CHECK_RATE_LIMIT = limiter.limit("20/minute")

# =====================================================
# Permission Policies
# =====================================================

@router.post(
    "/permissions",
    response_model=ApiSuccessResponse[None],
)
@CASBIN_RATE_LIMIT
async def add_permission(
    payload: PermissionRequest,
    org: CurrentOrg,
    request: Request,
):
    success = PolicyService.add_permission(
        role=payload.role,
        org_slug=str(org.slug),
        module=payload.module,
        action=payload.action,
    )

    logger.info(
        "Add permission: role=%s, org=%s, module=%s, action=%s, success=%s",
        payload.role,
        org.slug,
        payload.module,
        payload.action,
        success,
    )
    if not success:
        raise ConflictError(message="Permission already exists.")

    return ApiSuccessResponse(message="Permission added successfully.")


@router.delete(
    "/permissions",
    response_model=ApiSuccessResponse[None],
)
@CASBIN_RATE_LIMIT
async def remove_permission(
    payload: PermissionRequest,
    org: CurrentOrg,
    request: Request
):
    success = PolicyService.remove_permission(
        role=payload.role,
        org_slug=str(org.slug),
        module=payload.module,
        action=payload.action,
    )

    logger.info(
        "Remove permission: role=%s, org=%s, module=%s, action=%s, success=%s",
        payload.role,
        org.slug,
        payload.module,
        payload.action,
        success,
    )
    if not success:
        raise NotFoundError(message="Permission not found.")

    return ApiSuccessResponse(message="Permission removed successfully.")


@router.get(
    "/roles/{role}/permissions",
    response_model=ApiSuccessResponse[list[PermissionResponse]],
)
@CASBIN_RATE_LIMIT
async def get_permissions(
    role: str,
    org: CurrentOrg,
    request: Request
):
    permissions = PolicyService.get_permissions(role, str(org.slug))
    permissions = [PermissionResponse.model_validate({
        "role": policy[0],
        "org": policy[1],
        "resource": policy[2],
        "action": policy[3],
    }) for policy in permissions]

    return ApiSuccessResponse[list[PermissionResponse]](
        message="Permissions retrieved successfully.",
        data=permissions,
    )


# =====================================================
# User <-> Role Mapping
# =====================================================

@router.post(
    "/users/roles",
    response_model=ApiSuccessResponse[None],
)
@CASBIN_RATE_LIMIT
async def assign_role(
    payload: UserRoleRequest,
    db: DB,
    request: Request,
    org: CurrentOrg,
):
    
    user =await db.get(User, payload.user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    success = PolicyService.assign_role(
        user=user,
        role=payload.role,
        org_slug=str(org.slug),
    )

    logger.info(
        "Assign role: user_id=%s, role=%s, org=%s, success=%s",
        payload.user_id,
        payload.role,
        org.slug,
        success,
    )
    if not success:
        raise ConflictError(message="Role already assigned to user.")

    return ApiSuccessResponse(message="Role assigned successfully.")


@router.delete(
    "/users/roles",
    response_model=ApiSuccessResponse[None],
)
@CASBIN_RATE_LIMIT
async def revoke_role(
    payload: UserRoleRequest,
    db: DB,
    request: Request,
    org: CurrentOrg,
):
    user = await db.get(User, payload.user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    success = PolicyService.revoke_role(
        user_id=user.id,
        role=payload.role,
        org_slug=str(org.slug),
    )

    logger.info(
        "Revoke role: user_id=%s, role=%s, org=%s, success=%s",
        payload.user_id,
        payload.role,
        org.slug,
        success,
    )
    if not success:
        raise NotFoundError(message="Role assignment not found.")

    return ApiSuccessResponse(message="Role revoked successfully.")


@router.get(
    "/users/{user_id}/roles",
    response_model=ApiSuccessResponse[list[RoleResponse]],
)
@CASBIN_RATE_LIMIT
async def get_user_roles(
    user_id: HashId,
    db: DB,
    org: CurrentOrg,
    request: Request
):
    user =await db.get(User, user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    roles = PolicyService.get_user_roles(
        user_id=user.id,
        org_slug=str(org.slug),
    )
    roles = [RoleResponse.model_validate({
        "roles": roles,
        "org": str(org.slug),
    })]

    return ApiSuccessResponse[list[RoleResponse]](
        message="Roles retrieved successfully.",
        data=roles,
    )


@router.get(
    "/users/{user_id}/permissions",
    response_model=ApiSuccessResponse[list[PermissionResponse]],
)
@CASBIN_RATE_LIMIT
async def get_user_permissions(
    user_id: HashId,
    db: DB,
    org: CurrentOrg,
    request: Request
):
    user =await db.get(User, user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    permissions = PolicyService.get_user_permissions(
        user_id=user.id,
        org_slug=str(org.slug),
    )
    permissions = [PermissionResponse.model_validate({
        "role": policy[0],
        "org": policy[1],
        "resource": policy[2],
        "action": policy[3],
    }) for policy in permissions]

    return ApiSuccessResponse[list[PermissionResponse]](
        message="Permissions retrieved successfully.",
        data=permissions,
    )

# =====================================================
# Role Inheritance
# =====================================================

@router.post(
    "/role-inheritance",
    response_model=ApiSuccessResponse[None],
)
@CASBIN_RATE_LIMIT
async def inherit_role(
    payload: RoleInheritanceRequest,
    org: CurrentOrg,
    request: Request
):
    success = PolicyService.inherit_role(
        role=payload.role,
        parent_role=payload.parent_role,
        org_slug=str(org.slug),
    )

    logger.info(
        "Inherit role: role=%s, parent_role=%s, org=%s, success=%s",
        payload.role,
        payload.parent_role,
        org.slug,
        success,
    )
    if not success:
        raise ConflictError(message="Inheritance already exists.")

    return ApiSuccessResponse(message="Role inheritance added successfully.")


@router.delete(
    "/role-inheritance",
    response_model=ApiSuccessResponse[None],
)
@CASBIN_RATE_LIMIT
async def remove_role_inheritance(
    payload: RoleInheritanceRequest,
    org: CurrentOrg,
    request: Request
):
    success = PolicyService.remove_role_inheritance(
        role=payload.role,
        parent_role=payload.parent_role,
        org_slug=str(org.slug),
    )

    logger.info(
        "Remove role inheritance: role=%s, parent_role=%s, org=%s, success=%s",
        payload.role,
        payload.parent_role,
        org.slug,
        success,
    )
    if not success:
        raise NotFoundError(message="Inheritance relationship not found.")

    return ApiSuccessResponse(message="Role inheritance removed successfully.")


# =====================================================
# Authorization Checks
# =====================================================

@router.get(
    "/permissions/check",
)
@AUTHORIZATION_CHECK_RATE_LIMIT
async def check_my_permission(
    module: str,
    action: str,
    current_user: CurrentUser,
    org: CurrentOrg,
    request: Request
):
    allowed = PolicyService.has_permission(
        user=current_user,
        org_slug=str(org.slug),
        module=module,
        action=action,
    )

    return {
        "allowed": allowed,
    }


@router.post(
    "/permissions/check",
)
@AUTHORIZATION_CHECK_RATE_LIMIT
async def check_user_permission(
    payload: PermissionCheckRequest,
    db: DB,
    org: CurrentOrg,
    request: Request
):
    user = await db.get(User, payload.user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    allowed = PolicyService.has_permission(
        user=user,
        org_slug=str(org.slug),
        module=payload.module,
        action=payload.action,
    )

    return {
        "allowed": allowed,
    }