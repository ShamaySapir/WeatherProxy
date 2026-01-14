from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load settings on app startup."""
    settings = get_settings()
    # Settings are now initialized and accessible globally
    print(f"App started in {settings.environment} mode")
    yield


app = FastAPI(title="Weather Proxy", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
