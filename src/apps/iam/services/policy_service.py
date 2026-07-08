# app/services/policy_service.py

from typing import List, Dict
from src.core.enums import RBACRole
from ..casbin import enforcer
from src.apps.iam.models import User


class PolicyService:

    # -------------------------------------------------------------------------
    # Authorization Check (Unified Request Evaluation)
    # -------------------------------------------------------------------------

    @staticmethod
    def has_permission(
        user: User,
        org_slug: str,
        module: str,
        action: str,
    ) -> bool:
        """
        Evaluates permissions for a user within an organization and module.
        """
        if user.is_superuser:
            return True
        
        return enforcer.enforce(
            str(user.id),
            org_slug,
            module,
            action,
        )

    # -------------------------------------------------------------------------
    # Permission Policies (Organization Level)
    # -------------------------------------------------------------------------

    @staticmethod
    def add_org_permission(role: str, org_slug: str, module: str, action: str) -> bool:
        """Add a role permission policy for a given organization and module action."""
        return enforcer.add_policy(role, org_slug, module, action)

    @staticmethod
    def remove_org_permission(role: str, org_slug: str, module: str, action: str) -> bool:
        """Remove a role permission policy for a given organization and module action."""
        return enforcer.remove_policy(role, org_slug, module, action)

    @staticmethod
    def get_permissions(role: str, org_slug: str) -> List[List[str]]:
        """Gets permissions for a role within an organization."""
        return enforcer.get_filtered_policy(0, role, org_slug)

    # -------------------------------------------------------------------------
    # User <-> Organization Role Mapping
    # -------------------------------------------------------------------------

    @staticmethod
    def assign_org_role(user_id: int, role: RBACRole, org_slug: str) -> bool:
        """Assign an organization-scoped RBAC role to a user."""
        return enforcer.add_grouping_policy(str(user_id), role.value, org_slug)

    @staticmethod
    def revoke_org_role(user_id: int, role: RBACRole, org_slug: str) -> bool:
        """Revoke an organization-scoped RBAC role from a user."""
        return enforcer.remove_grouping_policy(str(user_id), role.value, org_slug)

    @staticmethod
    def get_user_org_roles(user_id: int, org_slug: str) -> List[RBACRole]:
        """
        Efficiently fetches strongly-typed ORG roles for a single user.
        O(1) lookup against Casbin indexes.
        """
        roles = enforcer.get_roles_for_user_in_domain(str(user_id), org_slug)
        typed_roles: List[RBACRole] = []
        
        for role in roles:
            try:
                typed_roles.append(RBACRole(role))
            except ValueError:
                continue
                
        return typed_roles
    
    @staticmethod
    def remove_user_from_org(user_id: int, org_slug: str) -> bool:
        """Remove all organization roles for a user in a specific organization."""
        roles = enforcer.get_roles_for_user_in_domain(str(user_id), org_slug)
        result = enforcer.delete_roles_for_user_in_domain(str(user_id), roles, org_slug)
        return bool(result) 
    # -------------------------------------------------------------------------
    # Implicit Permission Resolution
    # -------------------------------------------------------------------------

    @staticmethod
    def get_user_implicit_permissions(user_id: int, org_slug: str) -> List[List[str]]:
        """
        Retrieves all resolved/inherited permissions for a user within an organization.
        """
        return enforcer.get_implicit_permissions_for_user(str(user_id), org_slug)

    # -------------------------------------------------------------------------
    # Role Inheritance
    # -------------------------------------------------------------------------

    @staticmethod
    def inherit_role(role: str, parent_role: str, domain: str) -> bool:
        """Create role inheritance between two roles in the same domain."""
        return enforcer.add_grouping_policy(role, parent_role, domain)
    
    @staticmethod
    def remove_role_inheritance(role: str, parent_role: str, domain: str) -> bool:
        """Remove role inheritance mapping in a domain."""
        return enforcer.remove_grouping_policy(role, parent_role, domain)

    # -------------------------------------------------------------------------
    # Management & Validation Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def get_org_members_map(org_slug: str) -> Dict[int, List[RBACRole]]:
        """
        Returns a mapped ledger of users and their strongly-typed ORG roles.
        """
        policies = enforcer.get_filtered_grouping_policy(2, org_slug)
        role_map: Dict[int, List[RBACRole]] = {}
        
        for user_id, role, _org in policies:
            try:
                role_enum = RBACRole(role)
                role_map.setdefault(int(user_id), []).append(role_enum)
            except ValueError:
                # Log or skip if a role string exists in Casbin but isn't in our application enum
                continue
                
        return role_map
    
    
    @staticmethod
    def is_org_member(user: User, org_slug: str) -> bool:
        """Return whether the user has at least one role in the organization."""
        if user.is_superuser:
            return True
        user_roles = enforcer.get_roles_for_user_in_domain(str(user.id), org_slug)
        return len(user_roles) > 0

    @staticmethod
    def can_access_org_role(user: User, org_slug: str, required_role: RBACRole) -> bool:
        """Return whether a user has a specific organization-scoped role."""
        if user.is_superuser:
            return True
        user_roles = enforcer.get_roles_for_user_in_domain(str(user.id), org_slug)
        return required_role.value in user_roles
