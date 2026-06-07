from __future__ import annotations

from functools import lru_cache
from typing import Any, Annotated, Generic, TypeVar

from hashids import Hashids
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import BeforeValidator

from core.config import settings

T = TypeVar("T")

SlugStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]

RoleCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=100),
]

PasswordStr = Annotated[
    str,
    StringConstraints(strip_whitespace=False, min_length=8, max_length=256),
]

CursorStr = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

@lru_cache(maxsize=1)
def get_hashids() -> Hashids:
    return Hashids(
        salt=settings.HASHIDS_SALT,
        min_length=settings.HASHIDS_MIN_LENGTH,
    )


def encode_hashid(value: int) -> str:
    """Encode an internal bigint ID to its public hashid representation."""

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("HashId fields must contain a positive integer")

    encoded = get_hashids().encode(value)
    if not encoded:
        raise ValueError("Failed to encode HashId value")
    return encoded


def decode_hashid(value: Any) -> int:
    """Decode a public hashid back to the internal bigint value."""

    if isinstance(value, bool):
        raise ValueError("HashId values cannot be booleans")
    if isinstance(value, int):
        if value < 1:
            raise ValueError("HashId values must be positive integers")
        return value
    if not isinstance(value, str):
        raise ValueError("HashId values must be strings")

    decoded = get_hashids().decode(value)
    if len(decoded) != 1:
        raise ValueError("Invalid hashid value")
    return decoded[0]


HashId = Annotated[
    int,
    BeforeValidator(decode_hashid),
    PlainSerializer(encode_hashid, return_type=str),
]

class BaseSchema(BaseModel):
    """Define the shared Pydantic configuration used by API schemas.

    All request and response models inherit this base so extra input is rejected,
    ORM objects can be serialized directly, and public field aliases behave
    consistently across the application surface.
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )


class ApiSuccessResponse(BaseSchema, Generic[T]):
    """Represent the standard success envelope returned by API routes.

    Success responses include a human-readable message together with the route's
    structured payload so clients can handle all public-auth outcomes
    consistently.
    """

    message: str = Field(description="Human-readable success message.")
    data: T | None = Field(
        default=None,
        description="Structured response payload for the request.",
    )


class CursorPage(BaseSchema, Generic[T]):
    """Represent a cursor-paginated response envelope.

    This generic container standardizes list responses that return a bounded page
    of items together with an opaque cursor for the next page.
    """

    items: list[T] = Field(
        default_factory=list,
        description="The current page of result items.",
    )
    next_cursor: CursorStr | None = Field(
        default=None,
        description="Opaque cursor for the next page, or null when there are no more items.",
    )


class CursorPagination(BaseSchema):
    """Capture the shared cursor-pagination query contract.

    Endpoints that expose cursor-based traversal reuse this schema so page size
    and cursor handling remain uniform across resource collections.
    """

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of items to return.",
    )
    cursor: CursorStr | None = Field(
        default=None,
        description="Opaque cursor supplied by a previous list response.",
    )
