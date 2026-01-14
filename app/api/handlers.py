"""Exception handlers for error responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.core.errors import AppError

logger = logging.getLogger(__name__)


def _get_request_id(request: Request) -> str:
    # request_id is set by middleware; fallback to "-"
    return getattr(request.state, "request_id", "-")


def get_error_response(
    *,
    message: str,
    code: str,
    status_code: int,
    request_id: str,
) -> dict[str, Any]:
    """Create standard error envelope."""
    return {
        "error": {
            "code": code,
            "message": message,
            "status_code": status_code,
            "request_id": request_id,
        }
    }


async def app_error_handler(request: Request, exc: Exception) -> Response:
    """Handle AppError exceptions (expected errors)."""
    request_id = _get_request_id(request)

    if not isinstance(exc, AppError):
        # This handler is registered for AppError, so this should never happen.
        logger.error(
            "app_error_handler_received_non_app_error",
            extra={"request_id": request_id, "exc_type": type(exc).__name__},
        )
        raise exc

    # For expected application errors, WARNING is fine (not ERROR).
    logger.warning(
        "application_error code=%s status_code=%s path=%s",
        exc.code,
        exc.status_code,
        request.url.path,
        extra={
            "request_id": request_id,
            "error_code": exc.code,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

    error_response = get_error_response(
        message=exc.message,
        code=exc.code,
        status_code=exc.status_code,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=error_response)


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle unhandled exceptions (unexpected errors)."""
    request_id = _get_request_id(request)

    # Use logger.exception to capture stacktrace.
    logger.exception(
        "unhandled_exception path=%s",
        request.url.path,
        extra={"request_id": request_id, "path": request.url.path},
    )

    error_response = get_error_response(
        message="Unexpected error occurred.",
        code="internal_server_error",
        status_code=500,
        request_id=request_id,
    )
    return JSONResponse(status_code=500, content=error_response)
