from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from src.core.types import CursorStr

T = TypeVar("T")

class DeliveryResult(BaseModel):
    channel: str
    provider: str
    success: bool
    message_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseSchema(BaseModel):
    """Define the shared Pydantic configuration used by API schemas.

    All request and response models inherit this base so extra input is rejected,
    ORM objects can be serialized directly, and public field aliases behave
    consistently across the application surface.
    """

    model_config = ConfigDict(
        # extra="forbid",
        extra="ignore",
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
