from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from apps.iam.dependencies import require_module_permission
from apps.iam.models import User
from apps.iam.policy_service import PolicyService
from core.eums import RBACModule as Module
from core.dependencies import (
    DB,
    CurrentOrg,
    CurrentUser,
)

from core.types import (
    ApiSuccessResponse,
    BaseSchema,
    HashId,
)

router = APIRouter(
    prefix="/rbac",
    tags=["RBAC"],
    dependencies=[
        require_module_permission(Module.RBAC),
    ]
)


# =====================================================
# Schemas
# =====================================================

class PermissionRequest(BaseSchema):
    role: str
    module: str
    action: str


class UserRoleRequest(BaseSchema):
    user_id: HashId
    role: str


class RoleInheritanceRequest(BaseSchema):
    role: str
    parent_role: str


class PermissionCheckRequest(BaseSchema):
    user_id: HashId
    module: str
    action: str


# =====================================================
# Permission Policies
# =====================================================

@router.post(
    "/permissions",
    response_model=ApiSuccessResponse[None],
)
async def add_permission(
    payload: PermissionRequest,
    current_org: CurrentOrg,
):
    success = PolicyService.add_permission(
        role=payload.role,
        org=str(current_org.id),
        module=payload.module,
        action=payload.action,
    )

    return ApiSuccessResponse(
        message=(
            "Permission added successfully."
            if success
            else "Permission already exists."
        ),
    )


@router.delete(
    "/permissions",
    response_model=ApiSuccessResponse[None],
)
async def remove_permission(
    payload: PermissionRequest,
    current_org: CurrentOrg,
):
    success = PolicyService.remove_permission(
        role=payload.role,
        org=str(current_org.id),
        module=payload.module,
        action=payload.action,
    )

    return ApiSuccessResponse(
        message=(
            "Permission removed successfully."
            if success
            else "Permission was not found."
        ),
    )


@router.get(
    "/roles/{role}/permissions",
    response_model=ApiSuccessResponse[list[list[str]]],
)
async def get_permissions(
    role: str,
):
    permissions = PolicyService.get_permissions(role)

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
    current_org: CurrentOrg,
):
    user = db.get(User, payload.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    success = PolicyService.assign_role(
        user=user,
        role=payload.role,
        org=str(current_org.id),
    )

    return ApiSuccessResponse(
        message=(
            "Role assigned successfully."
            if success
            else "Role already assigned."
        ),
    )


@router.delete(
    "/users/roles",
    response_model=ApiSuccessResponse[None],
)
async def revoke_role(
    payload: UserRoleRequest,
    db: DB,
    current_org: CurrentOrg,
):
    user = db.get(User, payload.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    success = PolicyService.revoke_role(
        user=user,
        role=payload.role,
        org=str(current_org.id),
    )

    return ApiSuccessResponse(
        message=(
            "Role revoked successfully."
            if success
            else "Role assignment not found."
        ),
    )


@router.get(
    "/users/{user_id}/roles",
    response_model=ApiSuccessResponse[list[str]],
)
async def get_user_roles(
    user_id: HashId,
    db: DB,
    current_org: CurrentOrg,
):
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    roles = PolicyService.get_user_roles(
        user=user,
        org=str(current_org.id),
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
    current_org: CurrentOrg,
):
    success = PolicyService.inherit_role(
        role=payload.role,
        parent_role=payload.parent_role,
        org=str(current_org.id),
    )

    return ApiSuccessResponse(
        message=(
            "Role inheritance created successfully."
            if success
            else "Inheritance already exists."
        ),
    )


@router.delete(
    "/role-inheritance",
    response_model=ApiSuccessResponse[None],
)
async def remove_role_inheritance(
    payload: RoleInheritanceRequest,
    current_org: CurrentOrg,
):
    success = PolicyService.remove_role_inheritance(
        role=payload.role,
        parent_role=payload.parent_role,
        org=str(current_org.id),
    )

    return ApiSuccessResponse(
        message=(
            "Role inheritance removed successfully."
            if success
            else "Inheritance relationship not found."
        ),
    )


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
    current_org: CurrentOrg,
):
    allowed = PolicyService.has_permission(
        user=current_user,
        org=str(current_org.id),
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
    current_org: CurrentOrg,
):
    user = db.get(User, payload.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    allowed = PolicyService.has_permission(
        user=user,
        org=str(current_org.id),
        module=payload.module,
        action=payload.action,
    )

    return {
        "allowed": allowed,
    }