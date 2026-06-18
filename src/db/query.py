from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.orm import Session, selectinload


def col(attribute):
    return attribute


__all__ = [
    "Session",
    "selectinload",
    "and_",
    "col",
    "desc",
    "func",
    "or_",
    "select",
    "update",
]