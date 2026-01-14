from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from app.api import RequestIDMiddleware, app_error_handler, unhandled_exception_handler
from app.core import AppError, get_settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load settings and setup logging on app startup."""
    settings = get_settings()
    setup_logging(settings.log_level)
    app.state.settings = settings
    logger.info(
        "app_started environment=%s",
        settings.environment,
    )
    yield


app = FastAPI(title="Weather Proxy", lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)

# Register exception handlers

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
