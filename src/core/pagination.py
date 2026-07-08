from __future__ import annotations

from enum import Enum
from typing import Callable, Sequence, TypeVar

from sqlalchemy import asc
from sqlalchemy.sql import Select

from src.core.exceptions import ValidationError
from src.core.schemas import CursorPage, CursorPagination
from src.core.utils import decode_cursor, encode_cursor
from src.db.query import and_, desc, or_

ModelT = TypeVar("ModelT")
ResponseT = TypeVar("ResponseT")


class CursorSortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


def apply_id_cursor_filter(
    query: Select,
    pagination: CursorPagination,
    *,
    id_column,
    direction: CursorSortDirection,
) -> Select:
    if not pagination.cursor:
        return query

    _, cursor_id = _safe_decode_cursor(pagination.cursor)

    if direction == CursorSortDirection.DESC:
        return query.where(id_column < cursor_id)

    return query.where(id_column > cursor_id)


def apply_datetime_id_cursor_filter(
    query: Select,
    pagination: CursorPagination,
    *,
    datetime_column,
    id_column,
    direction: CursorSortDirection,
) -> Select:
    if not pagination.cursor:
        return query

    cursor_datetime, cursor_id = _safe_decode_cursor(pagination.cursor)
    if cursor_datetime is None:
        raise ValidationError(message="Invalid cursor. Missing created_at field.")

    if direction == CursorSortDirection.DESC:
        return query.where(
            or_(
                datetime_column < cursor_datetime,
                and_(datetime_column == cursor_datetime, id_column < cursor_id),
            )
        )

    return query.where(
        or_(
            datetime_column > cursor_datetime,
            and_(datetime_column == cursor_datetime, id_column > cursor_id),
        )
    )


def apply_ordering(query: Select, *, order_column, id_column, direction: CursorSortDirection) -> Select:
    if direction == CursorSortDirection.DESC:
        return query.order_by(desc(order_column), desc(id_column))

    return query.order_by(asc(order_column), asc(id_column))


def apply_id_ordering(query: Select, *, id_column, direction: CursorSortDirection) -> Select:
    if direction == CursorSortDirection.DESC:
        return query.order_by(desc(id_column))

    return query.order_by(asc(id_column))


def to_cursor_page(
    rows: Sequence[ModelT],
    pagination: CursorPagination,
    *,
    serializer: Callable[[ModelT], ResponseT],
    next_cursor_builder: Callable[[ModelT], str],
) -> CursorPage[ResponseT]:
    has_next_page = len(rows) > pagination.limit
    page_rows = rows[: pagination.limit] if has_next_page else rows

    items = [serializer(row) for row in page_rows]
    next_cursor = next_cursor_builder(page_rows[-1]) if has_next_page and page_rows else None

    return CursorPage[ResponseT](items=items, next_cursor=next_cursor)


def build_id_cursor(row, id_attr: str = "id") -> str:
    return encode_cursor(getattr(row, id_attr))


def build_datetime_id_cursor(row, id_attr: str = "id", created_at_attr: str = "created_at") -> str:
    return encode_cursor(getattr(row, id_attr), getattr(row, created_at_attr))


def _safe_decode_cursor(cursor: str) -> tuple[object | None, int]:
    try:
        cursor_datetime, cursor_id = decode_cursor(cursor)
        return cursor_datetime, int(cursor_id)
    except (ValueError, TypeError):
        raise ValidationError(message="Invalid cursor. Please use next_cursor from a previous response.")
