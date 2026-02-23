# Casbin RBAC Integration

This FastAPI project includes Casbin for Role-Based Access Control (RBAC).

## Overview

Casbin is an authorization library that supports various access control models. This integration uses the RBAC model with database persistence.

## Models

### Role Model
- `Role`: Represents a role (e.g., "admin", "editor", "viewer")
- Fields: id, name, description, created_at, updated_at

### Permission Model
- `Permission`: Represents a permission with resource and action
- Fields: id, resource, action, description, created_at
- Example: resource="users", action="read"

### UserRole Model
- Association table linking users to roles (many-to-many)
- Fields: id, user_id, role_id, assigned_at

### RolePermission Model
- Association table linking roles to permissions (many-to-many)
- Fields: id, role_id, permission_id, granted_at

### CasbinRule Model
- Stores Casbin policies and role mappings
- Automatically managed by Casbin adapter

## Usage

### Initialize Casbin Enforcer

```python
from src.apps.iam.casbin_enforcer import CasbinEnforcer
from src.db.session import engine

# Initialize enforcer (do this at app startup)
enforcer = await CasbinEnforcer.get_enforcer(engine)
```

### Using RBAC Utilities

```python
from src.apps.iam.utils.rbac import (
    assign_role_to_user,
    assign_permission_to_role,
    check_permission
)

# Assign a role to a user
await assign_role_to_user(user_id=1, role_id=2, session=session)

# Assign a permission to a role
await assign_permission_to_role(role_id=2, permission_id=5, session=session)

# Check if user has permission
has_permission = await check_permission(
    user_id=1,
    resource="users",
    action="read",
    session=session
)
```

### Using FastAPI Dependencies

```python
from fastapi import APIRouter, Depends
from src.apps.iam.utils.dependencies import require_permission, require_role

router = APIRouter()

# Require specific permission
@router.get("/users", dependencies=[Depends(require_permission("users", "read"))])
async def list_users():
    return {"users": []}

# Require specific role
@router.get("/admin", dependencies=[Depends(require_role("admin"))])
async def admin_panel():
    return {"message": "Admin access granted"}
```

### Direct Casbin Operations

```python
from src.apps.iam.casbin_enforcer import CasbinEnforcer

# Add a policy (role can perform action on resource)
await CasbinEnforcer.add_policy("admin", "users", "write")

# Add role to user
await CasbinEnforcer.add_role_for_user("user:1", "admin")

# Check permission
allowed = await CasbinEnforcer.enforce("user:1", "users", "write")

# Get all roles for a user
roles = await CasbinEnforcer.get_roles_for_user("user:1")

# Get all permissions for a user
permissions = await CasbinEnforcer.get_permissions_for_user("user:1")
```

## Casbin Model Configuration

The RBAC model is defined in `casbin_model.conf`:

```conf
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

This configuration means:
- **Request**: Check if subject (sub) can perform action (act) on object (obj)
- **Policy**: Define permissions as (subject, object, action)
- **Role**: Define role inheritance as (user, role)
- **Matcher**: User can access if they have the role that has the permission

## Database Migration

After adding these models, create and run a migration:

```bash
# Create migration
alembic revision --autogenerate -m "Add Casbin RBAC models"

# Apply migration
alembic upgrade head
```

## Example: Setting up roles and permissions

```python
from sqlmodel import Session
from src.apps.iam.models import Role, Permission, RolePermission
from src.apps.iam.utils.rbac import assign_role_to_user, assign_permission_to_role

# Create roles
admin_role = Role(name="admin", description="Administrator with full access")
editor_role = Role(name="editor", description="Can edit content")
viewer_role = Role(name="viewer", description="Can view content")

session.add_all([admin_role, editor_role, viewer_role])
await session.commit()

# Create permissions
read_users = Permission(resource="users", action="read", description="View users")
write_users = Permission(resource="users", action="write", description="Edit users")
delete_users = Permission(resource="users", action="delete", description="Delete users")

session.add_all([read_users, write_users, delete_users])
await session.commit()

# Assign permissions to roles
await assign_permission_to_role(admin_role.id, read_users.id, session)
await assign_permission_to_role(admin_role.id, write_users.id, session)
await assign_permission_to_role(admin_role.id, delete_users.id, session)
await assign_permission_to_role(editor_role.id, read_users.id, session)
await assign_permission_to_role(editor_role.id, write_users.id, session)
await assign_permission_to_role(viewer_role.id, read_users.id, session)

# Assign role to user
await assign_role_to_user(user_id=1, role_id=admin_role.id, session)
```

## Testing Permissions

```python
# Check if user can read users
can_read = await check_permission(
    user_id=1,
    resource="users",
    action="read",
    session=session
)

# Check if user can delete users
can_delete = await check_permission(
    user_id=1,
    resource="users",
    action="delete",
    session=session
)
```

## Benefits

1. **Flexible**: Easy to add/remove roles and permissions dynamically
2. **Scalable**: Efficient policy enforcement with Casbin
3. **Database-backed**: All policies persisted in database
4. **Type-safe**: Using SQLModel for type checking
5. **FastAPI Integration**: Easy to use with FastAPI dependencies
