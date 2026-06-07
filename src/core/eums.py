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

def enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return the string values for a Python enum."""

    return [member.value for member in enum_cls]
