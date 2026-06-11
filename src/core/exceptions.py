"""Shared application exception types used by services."""

from __future__ import annotations
from typing import Any


class AppError(Exception):
    """Base class for predictable application-level failures."""

    code = "app.error"
    status_code = 400

    def __init__(
            self, 
            message: str, 
            *, 
            code: str | None = None,
            details: Any | None = None,
            headers: dict[str, str] | None = None,
        ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.details = details
        self.headers = headers


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    code = "common.not_found"
    status_code = 404


class ConflictError(AppError):
    """Raised when a write collides with current state."""

    code = "common.conflict"
    status_code = 409


class AuthenticationError(AppError):
    """Raised when credentials or tokens are invalid."""

    code = "auth.invalid_credentials"
    status_code = 401


class AuthorizationError(AppError):
    """Raised when the actor is known but forbidden."""

    code = "auth.forbidden"
    status_code = 403


class ValidationError(AppError):
    """Raised when a request violates business validation rules."""

    code = "common.validation_error"
    status_code = 400

class RateLimitError(AppError):
    """Raised when a client exceeds allowed request limits."""

    code = "common.rate_limit_exceeded"
    status_code = 429