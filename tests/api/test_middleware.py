import logging

from fastapi.testclient import TestClient

from app.main import app


def test_health_includes_request_id_header():
    """Test that middleware adds X-Request-ID header to response."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]  # Should not be empty


def test_request_id_is_uuid_format():
    """Test that request_id is a valid UUID."""
    import uuid

    client = TestClient(app)
    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    # Should not raise ValueError if it's a valid UUID
    uuid.UUID(request_id)


def test_middleware_logs_request_with_duration(caplog):
    """Test that middleware logs include duration_ms."""
    client = TestClient(app)

    with caplog.at_level(logging.INFO):
        response = client.get("/health")

    assert response.status_code == 200
    # Check that logs contain duration information
    log_text = caplog.text.lower()
    assert "ms" in log_text or "duration" in log_text or "completed" in log_text
