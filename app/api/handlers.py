"""Exception handlers for error responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from app.core.errors import AppError
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

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


async def request_validation_error_handler(
    request: Request, exc: Exception
) -> Response:
    """Handle FastAPI request validation errors (e.g., wrong query param type)."""
    request_id = _get_request_id(request)

    if not isinstance(exc, RequestValidationError):
        raise exc

    logger.warning(
        "request_validation_error path=%s",
        request.url.path,
        extra={"request_id": request_id, "path": request.url.path},
    )

    # Optional: include exc.errors() in logs only, not in response (safer)
    logger.debug(
        "request_validation_details errors=%s",
        exc.errors(),
        extra={"request_id": request_id},
    )

    error_response = get_error_response(
        message="Invalid request.",
        code="validation_error",
        status_code=400,
        request_id=request_id,
    )
    return JSONResponse(status_code=400, content=error_response)


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle Starlette/FastAPI HTTPException errors (mostly 4xx)."""
    request_id = _get_request_id(request)

    if not isinstance(exc, StarletteHTTPException):
        raise exc

    # For 4xx this is expected, log as info/warning (not error)
    logger.info(
        "http_exception status_code=%s path=%s",
        exc.status_code,
        request.url.path,
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

    error_response = get_error_response(
        message=str(exc.detail),
        code="client_error",
        status_code=exc.status_code,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=error_response)


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
