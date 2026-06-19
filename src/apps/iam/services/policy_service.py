# app/services/policy_service.py

from src.core.eums import RBACRole

from ..casbin import enforcer
from src.apps.iam.models import User


class PolicyService:

    # -------------------------
    # Permission Policies
    # -------------------------

    @staticmethod
    def add_permission(
        role: str,
        org_slug: str,
        module: str,
        action: str,
    ) -> bool:
        return enforcer.add_policy(
            role,
            org_slug,
            module,
            action,
        )

    @staticmethod
    def remove_permission(
        role: str,
        org_slug: str,
        module: str,
        action: str,
    ) -> bool:
        return enforcer.remove_policy(
            role,
            org_slug,
            module,
            action,
        )

    @staticmethod
    def get_permissions(role: str,org_slug: str):
        return enforcer.get_filtered_policy(
            0,
            role,
            org_slug
        )

    # -------------------------
    # User <-> Role Mapping
    # -------------------------

    @staticmethod
    def assign_role(
        user_id: int,
        role: str,
        org_slug: str,
    ) -> bool:
        # TODO: Validate that the user belongs to the organization and that the role exists
        return enforcer.add_grouping_policy(
            user_id,
            role,
            org_slug,
        )

    @staticmethod
    def revoke_role(
        user_id: int,
        role: str,
        org_slug: str,
    ) -> bool:
        return enforcer.remove_grouping_policy(
            user_id,
            role,
            org_slug,
        )

    @staticmethod
    def get_user_roles(
        user_id: int,
        org_slug: str,
    ):
        return enforcer.get_roles_for_user_in_domain(
            user_id,
            org_slug,
        )
    
    @staticmethod
    def remove_user_with_roles(
        user_id: int,
        org_slug: str,
    ):
        roles = enforcer.get_roles_for_user_in_domain(
            user_id,
            org_slug,
        )
        return enforcer.delete_roles_for_user_in_domain(
            user_id,
            roles,
            org_slug,
        )

    # -------------------------
    # Role Inheritance
    # -------------------------

    @staticmethod
    def inherit_role(
        role: str,
        parent_role: str,
        org_slug: str,
    ) -> bool:
        return enforcer.add_grouping_policy(
            role,
            parent_role,
            org_slug,
        )
    
    @staticmethod
    def remove_role_inheritance(
        role: str,
        parent_role: str,
        org_slug: str,
    ) -> bool:
        return enforcer.remove_grouping_policy(
            role,
            parent_role,
            org_slug,
        )

    # -------------------------
    # Authorization Check
    # -------------------------

    @staticmethod
    def has_permission(
        user: User,
        org_slug: str,
        module: str,
        action: str,
    ) -> bool:
        
        if user.is_superuser:
            return True
        
        return enforcer.enforce(
            user.id,
            org_slug,
            module,
            action,
        )
    
    # ==========================
    # Organization Roles
    # ==========================

    @staticmethod
    @staticmethod
    def get_org_roles(org_slug: str) -> dict[int, list[RBACRole]]:
        """
        Returns:
        {
            1: ["admin"],
            2: ["manager", "editor"]
        }
        """

        policies = enforcer.get_filtered_grouping_policy(
            2,  # v2 = org/domain
            org_slug,
        )

        role_map: dict[int, list[RBACRole]] = {}

        for user_id, role, _org in policies:
            role_map.setdefault(user_id, []).append(role)

        return role_map