from src.core.enums import RBACRole
from src.core.types import  HashId
from src.core.schemas import BaseSchema

class PermissionRequest(BaseSchema):
    role: RBACRole
    module: str
    action: str


class UserRoleRequest(BaseSchema):
    user_id: HashId
    role: RBACRole


class RoleInheritanceRequest(BaseSchema):
    role: RBACRole
    parent_role: RBACRole


class PermissionCheckRequest(BaseSchema):
    user_id: HashId
    module: str
    action: str

class PermissionResponse(BaseSchema):
    role: str
    org: str
    resource: str
    action: str

class RoleResponse(BaseSchema):
    roles: list[str]
    org: str


