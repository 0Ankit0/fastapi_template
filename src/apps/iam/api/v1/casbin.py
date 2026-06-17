from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from src.apps.organizations.dependencies import get_current_org
from src.apps.organizations.models.organization import Organization
from src.apps.iam.dependencies import get_current_active_superuser, require_module_permission
from src.apps.iam.models import User
from src.apps.iam.services.policy_service import PolicyService
from src.core.eums import RBACModule as Module
from src.core.dependencies import (
    DB,
)
from src.core.logging import get_logger
from src.core.exceptions import NotFoundError, ConflictError
from src.core.schemas import ApiSuccessResponse
from src.core.types import (
    HashId,
)
from src.apps.iam.schemas.casbin import (
    PermissionRequest,
    UserRoleRequest,
    RoleInheritanceRequest,
    PermissionCheckRequest,
)

CurrentOrg = Annotated[Organization, Depends(get_current_org)]
CurrentUser = Annotated[User, Depends(get_current_active_superuser)]

router = APIRouter(
    prefix="/organizations/{org}/rbac",
    tags=["RBAC"],
    dependencies=[
        require_module_permission(Module.RBAC),
        # Depends(get_current_active_superuser)
    ]
)

logger = get_logger(__name__)




# =====================================================
# Permission Policies
# =====================================================

@router.post(
    "/permissions",
    response_model=ApiSuccessResponse[None],
)
async def add_permission(
    payload: PermissionRequest,
    org: CurrentOrg,
):
    success = PolicyService.add_permission(
        role=payload.role,
        org=str(org.id),
        module=payload.module,
        action=payload.action,
    )

    logger.info(
        "Add permission: role=%s, org=%s, module=%s, action=%s, success=%s",
        payload.role,
        org.id,
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
async def remove_permission(
    payload: PermissionRequest,
    org: CurrentOrg,
):
    success = PolicyService.remove_permission(
        role=payload.role,
        org=str(org.id),
        module=payload.module,
        action=payload.action,
    )

    logger.info(
        "Remove permission: role=%s, org=%s, module=%s, action=%s, success=%s",
        payload.role,
        org.id,
        payload.module,
        payload.action,
        success,
    )
    if not success:
        raise NotFoundError(message="Permission not found.")

    return ApiSuccessResponse(message="Permission removed successfully.")


@router.get(
    "/roles/{role}/permissions",
    response_model=ApiSuccessResponse[list[list[str]]],
)
async def get_permissions(
    role: str,
    org: CurrentOrg,
):
    permissions = PolicyService.get_permissions(role, str(org.id))

    return ApiSuccessResponse(
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
async def assign_role(
    payload: UserRoleRequest,
    db: DB,
    org: CurrentOrg,
):
    
    user =await db.get(User, payload.user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    success = PolicyService.assign_role(
        user=user,
        role=payload.role,
        org=str(org.id),
    )

    logger.info(
        "Assign role: user_id=%s, role=%s, org=%s, success=%s",
        payload.user_id,
        payload.role,
        org.id,
        success,
    )
    if not success:
        raise ConflictError(message="Role already assigned to user.")

    return ApiSuccessResponse(message="Role assigned successfully.")


@router.delete(
    "/users/roles",
    response_model=ApiSuccessResponse[None],
)
async def revoke_role(
    payload: UserRoleRequest,
    db: DB,
    org: CurrentOrg,
):
    user = await db.get(User, payload.user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    success = PolicyService.revoke_role(
        user=user,
        role=payload.role,
        org=str(org.id),
    )

    logger.info(
        "Revoke role: user_id=%s, role=%s, org=%s, success=%s",
        payload.user_id,
        payload.role,
        org.id,
        success,
    )
    if not success:
        raise NotFoundError(message="Role assignment not found.")

    return ApiSuccessResponse(message="Role revoked successfully.")


@router.get(
    "/users/{user_id}/roles",
    response_model=ApiSuccessResponse[list[str]],
)
async def get_user_roles(
    user_id: HashId,
    db: DB,
    org: CurrentOrg,
):
    user =await db.get(User, user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    roles = PolicyService.get_user_roles(
        user=user,
        org=str(org.id),
    )

    return ApiSuccessResponse(
        message="Roles retrieved successfully.",
        data=roles,
    )


# =====================================================
# Role Inheritance
# =====================================================

@router.post(
    "/role-inheritance",
    response_model=ApiSuccessResponse[None],
)
async def inherit_role(
    payload: RoleInheritanceRequest,
    org: CurrentOrg,
):
    success = PolicyService.inherit_role(
        role=payload.role,
        parent_role=payload.parent_role,
        org=str(org.id),
    )

    logger.info(
        "Inherit role: role=%s, parent_role=%s, org=%s, success=%s",
        payload.role,
        payload.parent_role,
        org.id,
        success,
    )
    if not success:
        raise ConflictError(message="Inheritance already exists.")

    return ApiSuccessResponse(message="Role inheritance added successfully.")


@router.delete(
    "/role-inheritance",
    response_model=ApiSuccessResponse[None],
)
async def remove_role_inheritance(
    payload: RoleInheritanceRequest,
    org: CurrentOrg,
):
    success = PolicyService.remove_role_inheritance(
        role=payload.role,
        parent_role=payload.parent_role,
        org=str(org.id),
    )

    logger.info(
        "Remove role inheritance: role=%s, parent_role=%s, org=%s, success=%s",
        payload.role,
        payload.parent_role,
        org.id,
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
async def check_my_permission(
    module: str,
    action: str,
    current_user: CurrentUser,
    org: CurrentOrg,
):
    allowed = PolicyService.has_permission(
        user=current_user,
        org=str(org.id),
        module=module,
        action=action,
    )

    return {
        "allowed": allowed,
    }


@router.post(
    "/permissions/check",
)
async def check_user_permission(
    payload: PermissionCheckRequest,
    db: DB,
    org: CurrentOrg,
):
    user = await db.get(User, payload.user_id)

    if not user:
        raise NotFoundError(message="User not found.")

    allowed = PolicyService.has_permission(
        user=user,
        org=str(org.id),
        module=payload.module,
        action=payload.action,
    )

    return {
        "allowed": allowed,
    }