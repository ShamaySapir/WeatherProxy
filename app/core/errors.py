"""Custom exception classes for error handling and mapping."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error.

    Attributes:
        message: Human-readable error message.
        code: Stable machine-readable code (snake_case).
        status_code: HTTP status code to return.
        details: Optional structured details (safe for logging/debug).
    """

    code: str = "internal_server_error"
    status_code: int = 500

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ValidationError(AppError):
    """Invalid input/validation error."""

    code = "validation_error"
    status_code = 400


class NotFoundError(AppError):
    """Resource not found error."""

    code = "not_found"
    status_code = 404


class UpstreamError(AppError):
    code = "upstream_error"
    status_code = 502

    def __init__(
        self,
        message: str = "Upstream service error",
        *,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        retryable: bool = True,
    ) -> None:
        self.retryable = retryable
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message, details=details)



class UpstreamTimeoutError(UpstreamError):
    """Upstream service timeout."""

    status_code = 504

    def __init__(
        self,
        message: str = "Upstream service timeout",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details, retryable=True)


class CircuitBreakerOpenError(AppError):
    """Circuit breaker is open."""

    code = "circuit_breaker_open"
    status_code = 503

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details=details)
