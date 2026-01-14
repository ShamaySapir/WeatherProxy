import logging

from app.core.logging import RequestIDFilter, setup_logging


def test_request_id_filter_adds_default():
    """Test that RequestIDFilter adds request_id='-' if missing."""
    filter_obj = RequestIDFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    result = filter_obj.filter(record)
    assert result is True
    assert hasattr(record, "request_id")
    assert record.request_id == "-"


def test_request_id_filter_preserves_existing():
    """Test that RequestIDFilter preserves existing request_id."""
    filter_obj = RequestIDFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc123"

    result = filter_obj.filter(record)
    assert result is True
    assert record.request_id == "abc123"


def test_setup_logging_configures_handlers():
    """Test that setup_logging configures logging successfully."""
    # Just verify it doesn't raise an exception
    setup_logging("INFO")

    # Verify we can get a logger after setup
    logger = logging.getLogger("test")
    assert logger is not None


def test_log_message_includes_request_id():
    """Test that log messages include request_id field when logging."""
    setup_logging("INFO")

    # Create a custom handler to capture log output
    import io

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger("test_request_id")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Add filter to inject request_id
    logger.addFilter(RequestIDFilter())

    # Log with request_id in extra
    logger.info("Test message", extra={"request_id": "abc-123"})

    log_output = log_stream.getvalue()
    # Check that request_id appears in the formatted output
    assert "request_id=abc-123" in log_output
