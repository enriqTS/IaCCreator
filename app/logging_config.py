"""Structured JSON logging configuration."""

import json
import logging
import os
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON with structured fields.

    Fields emitted: timestamp (ISO-8601 UTC), level, message, logger,
    correlation_id. Exception info is included when present.

    No PII, secrets, or request bodies are logged by this formatter.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", "anonymous"),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def configure_logging() -> None:
    """Set up structured JSON logging for the application.

    Reads the LOG_LEVEL environment variable (default: INFO) and configures
    the root logger with a StreamHandler using JSONFormatter.
    """
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(getattr(logging, level, logging.INFO))
