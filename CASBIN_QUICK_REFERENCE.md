# Casbin RBAC Quick Reference

## What Has Been Added

### 1. **Packages Installed**
- `casbin==1.43.0` - Core Casbin authorization library
- `pycasbin==2.8.0` - Python implementation of Casbin
- `casbin-sqlalchemy-adapter==1.4.0` - SQLAlchemy adapter for Casbin
- `casbin-async-sqlalchemy-adapter==1.17.0` - Async SQLAlchemy adapter for Casbin

### 2. **Database Models Created**

#### `src/apps/iam/models/role.py`
- **Role**: Main role table (id, name, description, timestamps)
- **Permission**: Permission table (id, resource, action, description)
- **UserRole**: Association table for user-role relationships
- **RolePermission**: Association table for role-permission relationships

#### `src/apps/iam/models/casbin_rule.py`
- **CasbinRule**: Stores Casbin policy rules (managed by Casbin adapter)

### 3. **Casbin Configuration**

#### `src/apps/iam/casbin_model.conf`
RBAC model configuration defining request, policy, role definitions, and matchers.

#### `src/apps/iam/casbin_enforcer.py`
Singleton enforcer class with methods:
- `get_enforcer()` - Initialize and get enforcer instance
- `add_policy()` - Add permission policy
- `remove_policy()` - Remove permission policy
- `add_role_for_user()` - Assign role to user
- `remove_role_for_user()` - Remove role from user
- `enforce()` - Check if action is allowed
- `get_roles_for_user()` - Get all roles for a user
- `get_permissions_for_user()` - Get all permissions for a user

### 4. **Utility Functions**

#### `src/apps/iam/utils/rbac.py`
- `get_user_roles()` - Get all roles for a user from database
- `get_role_permissions()` - Get all permissions for a role
- `assign_role_to_user()` - Assign role and update Casbin
- `remove_role_from_user()` - Remove role and update Casbin
- `assign_permission_to_role()` - Assign permission and update Casbin
- `remove_permission_from_role()` - Remove permission and update Casbin
- `check_permission()` - Check if user has permission

#### `src/apps/iam/utils/dependencies.py`
FastAPI dependency factories:
- `require_permission(resource, action)` - Require specific permission
- `require_role(role_name)` - Require specific role

### 5. **Initialization Utilities**

#### `src/apps/iam/casbin_init.py`
- `init_casbin()` - Context manager for FastAPI lifespan
- `setup_default_roles_and_permissions()` - Initialize default RBAC setup

## Next Steps

### Step 1: Run Database Migration
```bash
# Create migration
alembic revision --autogenerate -m "Add Casbin RBAC models"

# Apply migration
alembic upgrade head
```

### Step 2: Update main.py to Initialize Casbin
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.apps.iam.casbin_init import init_casbin

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with init_casbin(app):
        yield

app = FastAPI(lifespan=lifespan)
```

### Step 3: Setup Default Roles and Permissions (Optional)
```python
from src.db.session import get_session
from src.apps.iam.casbin_init import setup_default_roles_and_permissions

async with get_session() as session:
    await setup_default_roles_and_permissions(session)
```

### Step 4: Use in Your API Endpoints
```python
from fastapi import APIRouter, Depends
from src.apps.iam.utils.dependencies import require_permission, require_role

router = APIRouter()

@router.get("/users", dependencies=[Depends(require_permission("users", "read"))])
async def list_users():
    return {"users": []}

@router.post("/users", dependencies=[Depends(require_permission("users", "write"))])
async def create_user():
    return {"message": "User created"}

@router.get("/admin", dependencies=[Depends(require_role("admin"))])
async def admin_panel():
    return {"message": "Admin access"}
```

## Files Created
- `src/apps/iam/models/role.py` - Role and permission models
- `src/apps/iam/models/casbin_rule.py` - Casbin rule storage model
- `src/apps/iam/casbin_model.conf` - Casbin RBAC configuration
- `src/apps/iam/casbin_enforcer.py` - Casbin enforcer wrapper
- `src/apps/iam/casbin_init.py` - Initialization utilities
- `src/apps/iam/utils/rbac.py` - RBAC utility functions
- `src/apps/iam/utils/dependencies.py` - FastAPI dependencies
- `CASBIN_RBAC_README.md` - Comprehensive documentation
- `CASBIN_QUICK_REFERENCE.md` - This file

## Updated Files
- `pyproject.toml` - Added Casbin packages
- `src/apps/iam/models/__init__.py` - Export new models
- `src/apps/iam/models/user.py` - Added user_roles relationship

## Benefits
✅ Role-Based Access Control (RBAC)
✅ Dynamic permission management
✅ Database-backed policies
✅ Async/await support
✅ FastAPI integration
✅ Type-safe with SQLModel
✅ Scalable and efficient

For detailed documentation, see `CASBIN_RBAC_README.md`
