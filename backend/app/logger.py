"""
Centralized structured JSON logger and telemetry pipeline.

Implements Issue #21: [Telemetry & Observability] Implement Centralized Debug
Logging & Audit Ledger Pipeline.

Features:
- Structured JSON log formatting with ISO 8601 UTC timestamps.
- Console (sys.stdout) stream handler.
- Rotating file storage (logs/arena_debug.log, 50MB max, 3 backups).
- Sensitive data redaction (GROQ_API_KEY, secrets, Bearer tokens).
- In-memory thread-safe ring buffer (collections.deque, maxlen=50) for
  capturing recent WARNING and ERROR events.
- Administrative inspection access helper.
"""

from collections import deque
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import sys
import threading
from typing import Any

from app.config import get_settings

STANDARD_LOG_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

SENSITIVE_KEYS = {
    "authorization",
    "admin_token",
    "groq_api_key",
    "secret",
    "password",
    "api_key",
    "token",
}

BEARER_PATTERN = re.compile(r"(Bearer\s+)[^\s,;\"'\}]+", re.IGNORECASE)
GROQ_KEY_PATTERN = re.compile(r"gsk_[A-Za-z0-9_]{10,}")


def redact_text(text: str) -> str:
    """Scrub sensitive keys and tokens from a text string."""
    if not text:
        return text

    # Redact configured GROQ_API_KEY if present
    settings = get_settings()
    if settings.GROQ_API_KEY and len(settings.GROQ_API_KEY) > 5:
        text = text.replace(settings.GROQ_API_KEY, "[REDACTED_API_KEY]")

    # Redact Bearer tokens
    text = BEARER_PATTERN.sub(r"\1[REDACTED_TOKEN]", text)

    # Redact generic Groq API keys
    text = GROQ_KEY_PATTERN.sub("[REDACTED_API_KEY]", text)

    return text


def redact_data(obj: Any) -> Any:
    """Recursively scrub sensitive data from dictionaries, lists, and primitives."""
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, dict):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_KEYS:
                if isinstance(v, str) and v.lower().startswith("bearer "):
                    cleaned[k] = "Bearer [REDACTED_TOKEN]"
                else:
                    cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_data(v)
        return cleaned
    if isinstance(obj, (list, tuple)):
        return [redact_data(item) for item in obj]
    return obj


class JSONFormatter(logging.Formatter):
    """Formats log records as one-line JSON documents with UTC timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        data = self.record_to_dict(record)
        return json.dumps(data)

    def record_to_dict(self, record: logging.LogRecord) -> dict[str, Any]:
        """Convert a LogRecord to a dictionary ready for JSON serialization."""
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        iso_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        entry: dict[str, Any] = {
            "timestamp": iso_timestamp,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Merge custom attributes passed in extra={...}
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_ATTRS and not key.startswith("_"):
                entry[key] = value

        # Include traceback string if exception info was logged
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return redact_data(entry)


class RingBufferHandler(logging.Handler):
    """
    Thread-safe in-memory ring buffer holding recent warning/error events.

    Default capacity is 50 records. Used by the administrative endpoint
    GET /api/admin/recent-errors.
    """

    def __init__(self, capacity: int = 50) -> None:
        super().__init__(level=logging.WARNING)
        self.capacity = capacity
        self.buffer: deque[dict[str, Any]] = deque(maxlen=capacity)
        self.lock = threading.RLock()
        self.formatter = JSONFormatter()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = self.formatter.record_to_dict(record)
            with self.lock:
                self.buffer.append(entry)
        except Exception:
            self.handleError(record)

    def get_entries(self) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.buffer)

    def clear(self) -> None:
        with self.lock:
            self.buffer.clear()


# Global ring buffer instance for warning/error telemetry
ring_buffer_handler = RingBufferHandler(capacity=50)

# Arena application logger
logger = logging.getLogger("arena")


def setup_logging(
    log_file_path: str = "logs/arena_debug.log",
    log_level: int = logging.INFO,
) -> logging.Logger:
    """
    Configure the centralized arena logger with console, rotating file,
    and ring buffer handlers.
    """
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Avoid duplicate handlers if setup_logging is invoked multiple times
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    # 1. Console stream handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # 2. Rotating file handler (50MB max, 3 backups)
    try:
        dir_name = os.path.dirname(log_file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=50 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback if filesystem write is restricted
        print(f"Warning: Failed to initialize file logger at {log_file_path}: {e}", file=sys.stderr)

    # 3. In-memory ring buffer handler (captures WARNING & ERROR)
    logger.addHandler(ring_buffer_handler)

    return logger


# Initial bootstrap of logger
setup_logging()


def get_recent_errors() -> list[dict[str, Any]]:
    """Return the last 50 warning/error records from the in-memory ring buffer."""
    return ring_buffer_handler.get_entries()


def clear_recent_errors() -> None:
    """Clear the in-memory error ring buffer (useful for testing)."""
    ring_buffer_handler.clear()
