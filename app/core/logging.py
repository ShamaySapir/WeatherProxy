import logging
import logging.config


class RequestIDFilter(logging.Filter):
    """Add request_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject request_id if not present."""
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """Configure structured logging with request correlation."""
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"request_id_filter": {"()": RequestIDFilter}},
        "formatters": {
            "default": {
                "format": (
                    "%(asctime)s %(levelname)s %(name)s "
                    "request_id=%(request_id)s %(message)s"
                )
            }
        },
        "handlers": {
            "default": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "default",
                "filters": ["request_id_filter"],
            }
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": True,
            }
        },
    }

    logging.config.dictConfig(logging_config)
