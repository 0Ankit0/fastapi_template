from __future__ import annotations

from functools import lru_cache
from typing import Any, Annotated, TypeVar

from hashids import Hashids
from pydantic import  StringConstraints
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import BeforeValidator

from src.core.config import settings

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
