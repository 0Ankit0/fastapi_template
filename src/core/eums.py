"""Shared application enums used by models and schemas."""

from __future__ import annotations

from enum import Enum


class UserStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

class OrganizationMemberStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"

class RBACAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

class RBACRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

class RBACModule(str, Enum):
    USERS = "users"
    RBAC = "rbac"
    ORGANIZATIONS = "organizations"
    ORGANIZATION_MEMBERS = "organization_members"

class EmailProvider(str, Enum):
    SMTP = "smtp"

class PushProvider(str, Enum):
    FCM = "fcm"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return the string values for a Python enum."""

    return [member.value for member in enum_cls]
