from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.apps.iam.models import Permission, Role, RolePermission, User, UserRole
from src.apps.iam.rbac.enforcer import CasbinEnforcer, GLOBAL_DOMAIN
from src.apps.iam.rbac.service import assign_permission_to_role, assign_role_to_user
from src.db.query import select
from src.db.session import engine

DEFAULT_PERMISSION_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("rbac", "read", "View roles, permissions, policies, and assignment state."),
    ("rbac", "manage", "Create roles, permissions, policy bindings, and role assignments."),
    ("users", "read", "Review user accounts and profile details."),
    ("users", "manage", "Update user accounts, privileges, and access state."),
    ("tokens", "read", "Inspect active sessions and issued tokens."),
    ("tokens", "manage", "Revoke or manage active sessions and tokens."),
    ("notifications", "read", "Review notification configuration and delivery state."),
    ("notifications", "manage", "Manage notification content and delivery settings."),
    ("observability", "read", "View logs, incidents, and observability summaries."),
    ("observability", "manage", "Triage incidents and update observability state."),
    ("analytics", "read", "View analytics dashboards and reporting summaries."),
    ("system", "read", "Inspect system status and effective configuration."),
    ("tenants", "read", "Review tenant and organization membership state."),
    ("tenants", "manage", "Manage tenant membership and organization settings."),
    ("finance", "read", "Review finance and payment information."),
    ("finance", "manage", "Manage finance providers and payment workflows."),
)

DEFAULT_ROLE_GRANTS: dict[str, tuple[str, ...]] = {
    "platform_admin": tuple(f"{resource}:{action}" for resource, action, _ in DEFAULT_PERMISSION_CATALOG),
    "security_auditor": (
        "rbac:read",
        "users:read",
        "tokens:read",
        "observability:read",
        "observability:manage",
        "notifications:read",
    ),
    "support_analyst": (
        "users:read",
        "tokens:read",
        "notifications:read",
        "observability:read",
        "analytics:read",
        "system:read",
    ),
    "tenant_admin": (
        "tenants:read",
        "tenants:manage",
        "users:read",
    ),
}

DEFAULT_ROLE_DESCRIPTIONS: dict[str, str] = {
    "platform_admin": "Full platform administration across RBAC, users, observability, and operations.",
    "security_auditor": "Security-focused review access for incidents, tokens, and role posture.",
    "support_analyst": "Read-oriented operational access for support and reporting workflows.",
    "tenant_admin": "Organization and membership administration without full platform control.",
}


@asynccontextmanager
async def init_casbin(app: FastAPI):
    enforcer = await CasbinEnforcer.get_enforcer(engine)
    app.state.casbin_enforcer = enforcer
    yield


async def _get_or_create_role(session: AsyncSession, name: str, description: str) -> Role:
    role = (await session.execute(select(Role).where(Role.name == name))).scalars().first()
    if role:
        if description and role.description != description:
            role.description = description
            await session.commit()
            await session.refresh(role)
        return role

    role = Role(name=name, description=description)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


async def _get_or_create_permission(
    session: AsyncSession,
    resource: str,
    action: str,
    description: str,
) -> Permission:
    permission = (
        await session.execute(
            select(Permission).where(
                Permission.resource == resource,
                Permission.action == action,
            )
        )
    ).scalars().first()
    if permission:
        if description and permission.description != description:
            permission.description = description
            await session.commit()
            await session.refresh(permission)
        return permission

    permission = Permission(resource=resource, action=action, description=description)
    session.add(permission)
    await session.commit()
    await session.refresh(permission)
    return permission


async def _ensure_role_permissions(session: AsyncSession, role: Role) -> None:
    expected = set(DEFAULT_ROLE_GRANTS.get(role.name, ()))
    if not expected:
        return

    existing_permissions = await session.execute(
        select(Permission.resource, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
    )
    existing = {f"{resource}:{action}" for resource, action in existing_permissions.all()}

    for key in sorted(expected - existing):
        resource, action = key.split(":", 1)
        permission = (
            await session.execute(
                select(Permission).where(
                    Permission.resource == resource,
                    Permission.action == action,
                )
            )
        ).scalars().first()
        if permission and role.id and permission.id:
            await assign_permission_to_role(role.id, permission.id, session, GLOBAL_DOMAIN)


async def _sync_superusers_with_platform_admin(session: AsyncSession, platform_admin: Role) -> None:
    superusers = (await session.execute(select(User).where(User.is_superuser.is_(True)))).scalars().all()
    for user in superusers:
        existing = (
            await session.execute(
                select(UserRole).where(
                    UserRole.user_id == user.id,
                    UserRole.role_id == platform_admin.id,
                )
            )
        ).scalars().first()
        if not existing and user.id and platform_admin.id:
            await assign_role_to_user(user.id, platform_admin.id, session, GLOBAL_DOMAIN)


async def bootstrap_rbac_catalog(session: AsyncSession) -> None:
    for role_name, description in DEFAULT_ROLE_DESCRIPTIONS.items():
        await _get_or_create_role(session, role_name, description)

    for resource, action, description in DEFAULT_PERMISSION_CATALOG:
        await _get_or_create_permission(session, resource, action, description)

    roles = (await session.execute(select(Role).where(Role.name.in_(DEFAULT_ROLE_GRANTS.keys())))).scalars().all()
    for role in roles:
        await _ensure_role_permissions(session, role)

    platform_admin = next((role for role in roles if role.name == "platform_admin"), None)
    if platform_admin is not None:
        await _sync_superusers_with_platform_admin(session, platform_admin)


async def setup_default_roles_and_permissions(session: AsyncSession) -> None:
    await bootstrap_rbac_catalog(session)