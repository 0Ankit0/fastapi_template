from src.apps.iam.rbac.bootstrap import (
    bootstrap_rbac_catalog,
    init_casbin,
    setup_default_roles_and_permissions,
)
from src.apps.iam.rbac.dependencies import (
    get_current_rbac_admin,
    require_permission,
    require_role,
)
from src.apps.iam.rbac.enforcer import CasbinEnforcer, GLOBAL_DOMAIN
from src.apps.iam.rbac.service import (
    assign_permission_to_role,
    assign_role_to_user,
    check_permission,
    get_role_permissions,
    get_role_users,
    get_user_roles,
    list_role_permission_policies,
    remove_permission_from_role,
    remove_role_from_user,
    resolve_authorization_domain,
)

__all__ = [
    "GLOBAL_DOMAIN",
    "CasbinEnforcer",
    "assign_permission_to_role",
    "assign_role_to_user",
    "bootstrap_rbac_catalog",
    "check_permission",
    "get_current_rbac_admin",
    "get_role_permissions",
    "get_role_users",
    "get_user_roles",
    "init_casbin",
    "list_role_permission_policies",
    "remove_permission_from_role",
    "remove_role_from_user",
    "require_permission",
    "require_role",
    "resolve_authorization_domain",
    "setup_default_roles_and_permissions",
]