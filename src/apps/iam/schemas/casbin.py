from src.core.types import  HashId
from src.core.schemas import BaseSchema

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
