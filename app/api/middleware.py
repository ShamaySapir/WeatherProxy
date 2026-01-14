import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

request_id_contextvar: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Get the current request_id from context."""
    return request_id_contextvar.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to generate request IDs and log request lifecycle."""

    async def dispatch(self, request: Request, call_next):
        """Process request and log details."""
        request_id = str(uuid.uuid4())
        request_id_contextvar.set(request_id)

        logger = logging.getLogger(__name__)
        logger_adapter = logging.LoggerAdapter(logger, {"request_id": request_id})

        logger_adapter.info(
            f"{request.method} {request.url.path} started",
            extra={"request_id": request_id},
        )

        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        message = (
            f"{request.method} {request.url.path} completed with "
            f"{response.status_code} in {duration_ms:.2f}ms"
        )
        logger_adapter.info(message, extra={"request_id": request_id})

        response.headers["X-Request-ID"] = request_id
        return response
