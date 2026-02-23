from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from src.db.session import get_session
from src.apps.iam.models import User, Role, UserRole, Permission, RolePermission
from src.apps.iam.casbin_enforcer import CasbinEnforcer


async def get_user_roles(user_id: int, session: AsyncSession) -> list[Role]:
    """
    Get all roles assigned to a user.
    
    Args:
        user_id: User ID
        session: Database session
        
    Returns:
        list[Role]: List of roles assigned to the user
    """
    statement = (
        select(Role)
        .join(UserRole)
        .where(UserRole.user_id == user_id)
    )
    result = await session.execute(statement)
    roles = result.scalars().all()
    return list(roles)


async def get_role_permissions(role_id: int, session: AsyncSession) -> list[Permission]:
    """
    Get all permissions assigned to a role.
    
    Args:
        role_id: Role ID
        session: Database session
        
    Returns:
        list[Permission]: List of permissions assigned to the role
    """
    statement = (
        select(Permission)
        .join(RolePermission)
        .where(RolePermission.role_id == role_id)
    )
    result = await session.execute(statement)
    permissions = result.scalars().all()
    return list(permissions)


async def assign_role_to_user(
    user_id: int, 
    role_id: int, 
    session: AsyncSession
) -> UserRole:
    """
    Assign a role to a user and update Casbin policies.
    
    Args:
        user_id: User ID
        role_id: Role ID
        session: Database session
        
    Returns:
        UserRole: Created user-role association
        
    Raises:
        HTTPException: If user or role not found, or role already assigned
    """
    # Check if user exists
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if role exists
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if role already assigned
    statement = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    )
    result = await session.execute(statement)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role already assigned to user"
        )
    
    # Create user-role association
    user_role = UserRole(user_id=user_id, role_id=role_id)
    session.add(user_role)
    await session.commit()
    await session.refresh(user_role)
    
    # Update Casbin policy
    await CasbinEnforcer.add_role_for_user(str(user_id), role.name)
    
    return user_role


async def remove_role_from_user(
    user_id: int,
    role_id: int,
    session: AsyncSession
) -> bool:
    """
    Remove a role from a user and update Casbin policies.
    
    Args:
        user_id: User ID
        role_id: Role ID
        session: Database session
        
    Returns:
        bool: True if role was removed successfully
        
    Raises:
        HTTPException: If user-role association not found
    """
    # Find user-role association
    statement = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id
    )
    result = await session.execute(statement)
    user_role = result.scalar_one_or_none()
    
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not assigned to user"
        )
    
    # Get role name for Casbin
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Remove user-role association
    await session.delete(user_role)
    await session.commit()
    
    # Update Casbin policy
    await CasbinEnforcer.remove_role_for_user(str(user_id), role.name)
    
    return True


async def assign_permission_to_role(
    role_id: int,
    permission_id: int,
    session: AsyncSession
) -> RolePermission:
    """
    Assign a permission to a role and update Casbin policies.
    
    Args:
        role_id: Role ID
        permission_id: Permission ID
        session: Database session
        
    Returns:
        RolePermission: Created role-permission association
        
    Raises:
        HTTPException: If role or permission not found, or permission already assigned
    """
    # Check if role exists
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Check if permission exists
    permission = await session.get(Permission, permission_id)
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found"
        )
    
    # Check if permission already assigned
    statement = select(RolePermission).where(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id
    )
    result = await session.execute(statement)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission already assigned to role"
        )
    
    # Create role-permission association
    role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
    session.add(role_permission)
    await session.commit()
    await session.refresh(role_permission)
    
    # Update Casbin policy
    await CasbinEnforcer.add_policy(role.name, permission.resource, permission.action)
    
    return role_permission


async def remove_permission_from_role(
    role_id: int,
    permission_id: int,
    session: AsyncSession
) -> bool:
    """
    Remove a permission from a role and update Casbin policies.
    
    Args:
        role_id: Role ID
        permission_id: Permission ID
        session: Database session
        
    Returns:
        bool: True if permission was removed successfully
        
    Raises:
        HTTPException: If role-permission association not found
    """
    # Find role-permission association
    statement = select(RolePermission).where(
        RolePermission.role_id == role_id,
        RolePermission.permission_id == permission_id
    )
    result = await session.execute(statement)
    role_permission = result.scalar_one_or_none()
    
    if not role_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not assigned to role"
        )
    
    # Get role and permission for Casbin
    role = await session.get(Role, role_id)
    permission = await session.get(Permission, permission_id)
    
    if not role or not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role or permission not found"
        )
    
    # Remove role-permission association
    await session.delete(role_permission)
    await session.commit()
    
    # Update Casbin policy
    await CasbinEnforcer.remove_policy(role.name, permission.resource, permission.action)
    
    return True


async def check_permission(
    user_id: int,
    resource: str,
    action: str,
    session: AsyncSession
) -> bool:
    """
    Check if a user has permission to perform an action on a resource.
    
    Args:
        user_id: User ID
        resource: Resource identifier
        action: Action to perform
        session: Database session
        
    Returns:
        bool: True if the user has permission
    """
    return await CasbinEnforcer.enforce(str(user_id), resource, action)
