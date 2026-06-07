# app/services/policy_service.py

from .casbin import enforcer
from apps.iam.models import User


class PolicyService:

    # -------------------------
    # Permission Policies
    # -------------------------

    @staticmethod
    def add_permission(
        role: str,
        org: str,
        module: str,
        action: str,
    ) -> bool:
        return enforcer.add_policy(
            role,
            org,
            module,
            action,
        )

    @staticmethod
    def remove_permission(
        role: str,
        org: str,
        module: str,
        action: str,
    ) -> bool:
        return enforcer.remove_policy(
            role,
            org,
            module,
            action,
        )

    @staticmethod
    def get_permissions(role: str):
        return enforcer.get_filtered_policy(
            0,
            role,
        )

    # -------------------------
    # User <-> Role Mapping
    # -------------------------

    @staticmethod
    def assign_role(
        user: User,
        role: str,
        org: str,
    ) -> bool:
        return enforcer.add_grouping_policy(
            user.id,
            role,
            org,
        )

    @staticmethod
    def revoke_role(
        user: User,
        role: str,
        org: str,
    ) -> bool:
        return enforcer.remove_grouping_policy(
            user.id,
            role,
            org,
        )

    @staticmethod
    def get_user_roles(
        user: User,
        org: str,
    ):
        return enforcer.get_roles_for_user_in_domain(
            user.id,
            org,
        )

    # -------------------------
    # Authorization Check
    # -------------------------

    @staticmethod
    def has_permission(
        user: User,
        org: str,
        module: str,
        action: str,
    ) -> bool:
        
        if user.is_superuser:
            return True
        
        return enforcer.enforce(
            user.id,
            org,
            module,
            action,
        )