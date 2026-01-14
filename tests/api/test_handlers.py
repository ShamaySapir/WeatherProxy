"""Tests for exception handlers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    CircuitBreakerOpenError,
    NotFoundError,
    UpstreamTimeoutError,
    ValidationError,
)


def test_validation_error_handler():
    """Test ValidationError returns 400 with proper envelope."""
    app = FastAPI()

    from app.api import app_error_handler
    from app.core import AppError

    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/test")
    async def test_endpoint():
        raise ValidationError("Invalid city name")

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "validation_error"
    assert data["error"]["status_code"] == 400
    assert "request_id" in data["error"]


def test_not_found_error_handler():
    """Test NotFoundError returns 404."""
    app = FastAPI()

    from app.api import app_error_handler
    from app.core import AppError

    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/test")
    async def test_endpoint():
        raise NotFoundError("City not found")

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "not_found"


def test_upstream_timeout_error_handler():
    """Test UpstreamTimeoutError returns 504."""
    app = FastAPI()

    from app.api import app_error_handler
    from app.core import AppError

    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/test")
    async def test_endpoint():
        raise UpstreamTimeoutError()

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 504
    data = response.json()
    assert data["error"]["code"] == "upstream_error"


def test_circuit_breaker_error_handler():
    """Test CircuitBreakerOpenError returns 503."""
    app = FastAPI()

    from app.api import app_error_handler
    from app.core import AppError

    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/test")
    async def test_endpoint():
        raise CircuitBreakerOpenError()

    client = TestClient(app)
    response = client.get("/test")

    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "circuit_breaker_open"


def test_error_envelope_format():
    """Test error envelope has all required fields."""
    app = FastAPI()

    from app.api import app_error_handler
    from app.core import AppError

    app.add_exception_handler(AppError, app_error_handler)

    @app.get("/test")
    async def test_endpoint():
        raise ValidationError("Test error")

    client = TestClient(app)
    response = client.get("/test")

    data = response.json()
    error = data["error"]

    assert "code" in error
    assert "message" in error
    assert "status_code" in error
    assert "request_id" in error
    assert error["message"] == "Test error"
