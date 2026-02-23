"""
Example API endpoints demonstrating Casbin RBAC usage.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from pydantic import BaseModel
from src.db.session import get_session
from src.apps.iam.models import Role, Permission, User
from src.apps.iam.utils.rbac import (
    assign_role_to_user,
    remove_role_from_user,
    assign_permission_to_role,
    remove_permission_from_role,
    get_user_roles,
    get_role_permissions,
    check_permission
)
from src.apps.iam.casbin_enforcer import CasbinEnforcer
from src.apps.core.schemas import PaginatedResponse
from src.apps.core.cache import RedisCache


router = APIRouter(prefix="/rbac", tags=["RBAC"])


class RoleCreate(BaseModel):
    name: str
    description: str = ""


class PermissionCreate(BaseModel):
    resource: str
    action: str
    description: str = ""


class RoleAssignment(BaseModel):
    user_id: int
    role_id: int


class PermissionAssignment(BaseModel):
    role_id: int
    permission_id: int


# ==== Role Management ====

@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new role"""
    role = Role(name=role_data.name, description=role_data.description)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    
    # Invalidate roles list cache
    await RedisCache.clear_pattern("roles:list:*")
    
    return {"message": "Role created", "role": role}


@router.get("/roles", response_model=PaginatedResponse[Role])
async def list_roles(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of items to return"),
    session: AsyncSession = Depends(get_session)
):
    """List all roles with pagination"""
    cache_key = f"roles:list:{skip}:{limit}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    # Get total count
    count_result = await session.execute(select(func.count(Role.id))) # type: ignore
    total = count_result.scalar_one()
    
    # Get paginated data
    result = await session.execute(
        select(Role)
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    
    # Create response
    response = PaginatedResponse[Role].create(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Cache for 10 minutes
    await RedisCache.set(cache_key, response.model_dump(), ttl=600)
    
    return response


@router.get("/roles/{role_id}")
async def get_role(role_id: int, session: AsyncSession = Depends(get_session)):
    """Get role details"""
    cache_key = f"role:{role_id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return {"role": Role(**cached)}
    
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Cache for 15 minutes
    await RedisCache.set(cache_key, role.model_dump(), ttl=900)
    
    return {"role": role}


# ==== Permission Management ====

@router.post("/permissions", status_code=status.HTTP_201_CREATED)
async def create_permission(
    perm_data: PermissionCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new permission"""
    permission = Permission(
        resource=perm_data.resource,
        action=perm_data.action,
        description=perm_data.description
    )
    session.add(permission)
    await session.commit()
    await session.refresh(permission)
    
    # Invalidate permissions list cache
    await RedisCache.clear_pattern("permissions:list:*")
    
    return {"message": "Permission created", "permission": permission}


@router.get("/permissions", response_model=PaginatedResponse[Permission])
async def list_permissions(
    skip: int = Query(default=0, ge=0, description="Number of items to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Number of items to return"),
    session: AsyncSession = Depends(get_session)
):
    """List all permissions with pagination"""
    cache_key = f"permissions:list:{skip}:{limit}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    # Get total count
    count_result = await session.execute(select(func.count(Permission.id))) # type: ignore
    total = count_result.scalar_one()
    
    # Get paginated data
    result = await session.execute(
        select(Permission)
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    
    # Create response
    response = PaginatedResponse[Permission].create(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )
    
    # Cache for 10 minutes
    await RedisCache.set(cache_key, response.model_dump(), ttl=600)
    
    return response


# ==== Role-User Assignment ====

@router.post("/users/assign-role")
async def assign_role(
    assignment: RoleAssignment,
    session: AsyncSession = Depends(get_session)
):
    """Assign a role to a user"""
    user_role = await assign_role_to_user(
        user_id=assignment.user_id,
        role_id=assignment.role_id,
        session=session
    )
    
    # Invalidate user roles cache
    await RedisCache.clear_pattern(f"user:{assignment.user_id}:roles*")
    await RedisCache.delete(f"casbin:roles:{assignment.user_id}")
    
    return {"message": "Role assigned to user", "user_role": user_role}


@router.delete("/users/remove-role")
async def remove_role(
    assignment: RoleAssignment,
    session: AsyncSession = Depends(get_session)
):
    """Remove a role from a user"""
    result = await remove_role_from_user(
        user_id=assignment.user_id,
        role_id=assignment.role_id,
        session=session
    )
    
    # Invalidate user roles cache
    await RedisCache.clear_pattern(f"user:{assignment.user_id}:roles*")
    await RedisCache.delete(f"casbin:roles:{assignment.user_id}")
    
    return {"message": "Role removed from user", "success": result}


@router.get("/users/{user_id}/roles")
async def get_user_roles_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get all roles for a user"""
    cache_key = f"user:{user_id}:roles"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    roles = await get_user_roles(user_id, session)
    
    response = {"user_id": user_id, "roles": roles}
    
    # Cache for 5 minutes
    await RedisCache.set(cache_key, response, ttl=300)
    
    return response


# ==== Permission-Role Assignment ====

@router.post("/roles/assign-permission")
async def assign_permission(
    assignment: PermissionAssignment,
    session: AsyncSession = Depends(get_session)
):
    """Assign a permission to a role"""
    role_permission = await assign_permission_to_role(
        role_id=assignment.role_id,
        permission_id=assignment.permission_id,
        session=session
    )
    
    # Invalidate role permissions cache
    await RedisCache.clear_pattern(f"role:{assignment.role_id}:permissions*")
    
    return {"message": "Permission assigned to role", "role_permission": role_permission}


@router.delete("/roles/remove-permission")
async def remove_permission(
    assignment: PermissionAssignment,
    session: AsyncSession = Depends(get_session)
):
    """Remove a permission from a role"""
    result = await remove_permission_from_role(
        role_id=assignment.role_id,
        permission_id=assignment.permission_id,
        session=session
    )
    
    # Invalidate role permissions cache
    await RedisCache.clear_pattern(f"role:{assignment.role_id}:permissions*")
    
    return {"message": "Permission removed from role", "success": result}


@router.get("/roles/{role_id}/permissions")
async def get_role_permissions_endpoint(
    role_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get all permissions for a role"""
    cache_key = f"role:{role_id}:permissions"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    permissions = await get_role_permissions(role_id, session)
    
    response = {"role_id": role_id, "permissions": permissions}
    
    # Cache for 5 minutes
    await RedisCache.set(cache_key, response, ttl=300)
    
    return response


# ==== Permission Checking ====

@router.get("/check-permission/{user_id}")
async def check_user_permission(
    user_id: int,
    resource: str,
    action: str,
    session: AsyncSession = Depends(get_session)
):
    """Check if a user has a specific permission"""
    cache_key = f"permission:check:{user_id}:{resource}:{action}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached is not None:
        return cached
    
    has_permission = await check_permission(user_id, resource, action, session)
    
    response = {
        "user_id": user_id,
        "resource": resource,
        "action": action,
        "allowed": has_permission
    }
    
    # Cache for 2 minutes (short TTL for permissions)
    await RedisCache.set(cache_key, response, ttl=120)
    
    return response


# ==== Casbin Direct Operations ====

@router.get("/casbin/roles/{user_id}")
async def get_casbin_roles(user_id: int):
    """Get roles from Casbin for a user"""
    cache_key = f"casbin:roles:{user_id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    roles = await CasbinEnforcer.get_roles_for_user(str(user_id))
    
    response = {"user_id": user_id, "roles": roles}
    
    # Cache for 5 minutes
    await RedisCache.set(cache_key, response, ttl=300)
    
    return response


@router.get("/casbin/permissions/{user_id}")
async def get_casbin_permissions(user_id: int):
    """Get all permissions from Casbin for a user"""
    cache_key = f"casbin:permissions:{user_id}"
    
    # Try cache
    cached = await RedisCache.get(cache_key)
    if cached:
        return cached
    
    permissions = await CasbinEnforcer.get_permissions_for_user(str(user_id))
    
    response = {"user_id": user_id, "permissions": permissions}
    
    # Cache for 5 minutes
    await RedisCache.set(cache_key, response, ttl=300)
    
    return response
