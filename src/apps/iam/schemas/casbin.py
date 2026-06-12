from src.core.types import BaseSchema, HashId

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
