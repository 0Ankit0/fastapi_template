"""HTTP exception handlers for consistent API error responses."""

from __future__ import annotations

from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import AppError
from .logging import get_logger


logger = get_logger(__name__)

def error_body(*, code: str, message: str, details: object | None = None) -> dict[str, Any]:
    """Build the API's standard error response body.

    Args:
        code: Machine-readable application error code.
        message: Human-readable message safe to return to clients.
        details: Optional structured details for validation or debugging.

    Returns:
        A JSON-serializable dictionary in the shared error envelope format.
    """

    error: dict[str, Any] = {
        "code": code,
        "message": message,
    }
    body: dict[str, Any] = {"error": error}
    if details is not None:
        error["details"] = details

    return body

async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Serialize one application exception into the standard API response.

    Args:
        request: Incoming HTTP request.
        exc: Exception instance registered for the :class:`AppError` handler.

    Returns:
        A JSON response built from the application exception fields.
    """

    app_exc = cast(AppError, exc)
    logger.warning(
        "App error on %s %s: code=%s status=%s message=%s",
        request.method,
        request.url.path,
        app_exc.code,
        app_exc.status_code,
        app_exc.message,
    )
    return JSONResponse(
        status_code=app_exc.status_code,
        content=error_body(
            code=app_exc.code,
            message=app_exc.message,
            details=getattr(app_exc, "details", None),
        ),
        headers=getattr(app_exc, "headers", None),
    )

async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Serialize a request validation failure into the standard API response.

    Args:
        request: Incoming HTTP request.
        exc: Exception instance registered for the validation-error handler.

    Returns:
        A JSON response with standardized validation error payload.
    """

    _ = request
    validation_exc = cast(RequestValidationError, exc)
    return JSONResponse(
        status_code=422,
        content=error_body(
            code="common.invalid_request",
            message="Request validation failed.",
            details=validation_exc.errors(),
        ),
    )

async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Serialize one Starlette HTTP exception into the standard API response.

    Args:
        request: Incoming HTTP request.
        exc: Exception instance registered for Starlette HTTP exceptions.

    Returns:
        A JSON response with standardized HTTP error payload.
    """

    _ = request
    http_exc = cast(StarletteHTTPException, exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=error_body(
            code="http_error",
            message=str(http_exc.detail),
        ),
        headers=http_exc.headers,
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic 500 response for unexpected exceptions.

    Args:
        request: Incoming HTTP request.
        exc: Unhandled exception raised by application code.

    Returns:
        A JSON response with a generic internal-error payload.
    """

    logger.error("Unhandled exception for %s", request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=error_body(
            code="common.internal_error",
            message="An unexpected error occurred.",
        ),
    )

def register_exception_handlers(app: FastAPI) -> None:
    """Register the application's exception handlers on a FastAPI app.

    Args:
        app: FastAPI application instance.
    """

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)