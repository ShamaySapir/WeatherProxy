"""Tests for custom error classes."""

from app.core.errors import (
    AppError,
    CircuitBreakerOpenError,
    NotFoundError,
    UpstreamError,
    UpstreamTimeoutError,
    ValidationError,
)


def test_validation_error():
    """Test ValidationError is 400."""
    exc = ValidationError("Invalid input")
    assert exc.status_code == 400
    assert exc.code == "validation_error"
    assert exc.message == "Invalid input"


def test_not_found_error():
    """Test NotFoundError is 404."""
    exc = NotFoundError("City not found")
    assert exc.status_code == 404
    assert exc.code == "not_found"
    assert exc.message == "City not found"


def test_upstream_timeout_error():
    """Test UpstreamTimeoutError is 504."""
    exc = UpstreamTimeoutError()
    assert exc.status_code == 504
    assert exc.code == "upstream_error"


def test_upstream_error_502():
    """Test UpstreamError defaults to 502."""
    exc = UpstreamError("Bad gateway")
    assert exc.status_code == 502
    assert exc.code == "upstream_error"


def test_circuit_breaker_open_error():
    """Test CircuitBreakerOpenError is 503."""
    exc = CircuitBreakerOpenError()
    assert exc.status_code == 503
    assert exc.code == "circuit_breaker_open"


def test_app_error_base():
    """Test AppError base class."""
    exc = AppError("Custom error")
    assert exc.status_code == 500
    assert exc.code == "internal_server_error"
    assert exc.message == "Custom error"
