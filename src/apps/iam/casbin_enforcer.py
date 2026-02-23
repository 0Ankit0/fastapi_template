from typing import Optional
import casbin
from casbin_async_sqlalchemy_adapter import Adapter as AsyncAdapter
from sqlalchemy.ext.asyncio import AsyncEngine
from pathlib import Path


class CasbinEnforcer:
    """
    Casbin Enforcer singleton for managing authorization policies.
    Supports RBAC (Role-Based Access Control) model.
    """
    
    _enforcer: Optional[casbin.AsyncEnforcer] = None
    
    @classmethod
    async def get_enforcer(cls, engine: AsyncEngine) -> casbin.AsyncEnforcer:
        """
        Get or create Casbin enforcer instance.
        
        Args:
            engine: SQLAlchemy async engine for database connection
            
        Returns:
            casbin.AsyncEnforcer: Configured Casbin enforcer instance
        """
        if cls._enforcer is None:
            # Get the path to the Casbin model configuration file
            model_path = Path(__file__).parent / "casbin_model.conf"
            
            # Initialize the async adapter with the database engine
            adapter = AsyncAdapter(engine, db_class=None)
            
            # Create the enforcer with model and adapter
            cls._enforcer = casbin.AsyncEnforcer(str(model_path), adapter)
            
            # Load policies from database
            await cls._enforcer.load_policy()
        
        return cls._enforcer
    
    @classmethod
    async def add_policy(cls, sub: str, obj: str, act: str) -> bool:
        """
        Add a policy rule.
        
        Args:
            sub: Subject (user ID or role name)
            obj: Object (resource)
            act: Action (read, write, delete, etc.)
            
        Returns:
            bool: True if policy was added successfully
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        result = await cls._enforcer.add_policy(sub, obj, act)
        return result
    
    @classmethod
    async def remove_policy(cls, sub: str, obj: str, act: str) -> bool:
        """
        Remove a policy rule.
        
        Args:
            sub: Subject (user ID or role name)
            obj: Object (resource)
            act: Action (read, write, delete, etc.)
            
        Returns:
            bool: True if policy was removed successfully
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        result = await cls._enforcer.remove_policy(sub, obj, act)
        return result
    
    @classmethod
    async def add_role_for_user(cls, user: str, role: str) -> bool:
        """
        Add a role for a user (grouping policy).
        
        Args:
            user: User identifier
            role: Role name
            
        Returns:
            bool: True if role was added successfully
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        result = await cls._enforcer.add_grouping_policy(user, role)
        return result
    
    @classmethod
    async def remove_role_for_user(cls, user: str, role: str) -> bool:
        """
        Remove a role from a user.
        
        Args:
            user: User identifier
            role: Role name
            
        Returns:
            bool: True if role was removed successfully
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        result = await cls._enforcer.delete_role_for_user(user, role)
        return result
    
    @classmethod
    async def get_roles_for_user(cls, user: str) -> list[str]:
        """
        Get all roles for a user.
        
        Args:
            user: User identifier
            
        Returns:
            list[str]: List of role names
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        roles = await cls._enforcer.get_roles_for_user(user)
        return roles
    
    @classmethod
    async def get_users_for_role(cls, role: str) -> list[str]:
        """
        Get all users for a role.
        
        Args:
            role: Role name
            
        Returns:
            list[str]: List of user identifiers
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        users = await cls._enforcer.get_users_for_role(role)
        return users
    
    @classmethod
    async def enforce(cls, sub: str, obj: str, act: str) -> bool:
        """
        Check if a user has permission to perform an action on a resource.
        
        Args:
            sub: Subject (user ID)
            obj: Object (resource)
            act: Action (read, write, delete, etc.)
            
        Returns:
            bool: True if the action is allowed
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        result = cls._enforcer.enforce(sub, obj, act)
        return result
    
    @classmethod
    async def get_permissions_for_user(cls, user: str) -> list[list[str]]:
        """
        Get all permissions for a user (includes inherited permissions from roles).
        
        Args:
            user: User identifier
            
        Returns:
            list[list[str]]: List of permission rules [sub, obj, act]
        """
        if cls._enforcer is None:
            raise RuntimeError("Enforcer not initialized. Call get_enforcer first.")
        
        permissions = await cls._enforcer.get_permissions_for_user(user)
        return permissions
