"""Central secure logging configuration for EcoBuddy AI."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from typing import Any

from log_sanitizer import (
    get_operation_id,
    sanitize_data,
    sanitize_string,
)


LOG_DIR = os.environ.get("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "ecobuddy.log")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").strip().lower()
LOG_MASK_EMAILS = (
    os.environ.get("LOG_MASK_EMAILS", "true").strip().lower()
    not in {"0", "false", "no"}
)

_STANDARD_KEYS = set(logging.makeLogRecord({}).__dict__.keys())


class SecureLogFilter(logging.Filter):
    """Attach operation IDs and sanitize all record data."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.operation_id = get_operation_id() or "-"

        # Render first so secrets supplied through %-format arguments can be
        # recognized together with their key in the message template.
        try:
            rendered_message = record.getMessage()
        except (TypeError, ValueError):
            rendered_message = str(record.msg)

        record.msg = sanitize_string(
            rendered_message,
            mask_emails=LOG_MASK_EMAILS,
        )
        record.args = ()

        for key, value in list(record.__dict__.items()):
            if key in _STANDARD_KEYS or key in {
                "message",
                "asctime",
                "operation_id",
            }:
                continue
            record.__dict__[key] = sanitize_data(
                value,
                mask_emails=LOG_MASK_EMAILS,
            )

        if record.stack_info:
            record.stack_info = sanitize_string(
                record.stack_info,
                mask_emails=LOG_MASK_EMAILS,
            )

        return True


class SecureTextFormatter(logging.Formatter):
    """Text formatter that sanitizes the full rendered traceback."""

    def formatException(self, exc_info) -> str:
        return sanitize_string(
            super().formatException(exc_info),
            mask_emails=LOG_MASK_EMAILS,
        )

    def formatStack(self, stack_info: str) -> str:
        return sanitize_string(
            super().formatStack(stack_info),
            mask_emails=LOG_MASK_EMAILS,
        )


class JsonLogFormatter(logging.Formatter):
    """Format structured logs as one JSON object per line."""

    def formatException(self, exc_info) -> str:
        return sanitize_string(
            super().formatException(exc_info),
            mask_emails=LOG_MASK_EMAILS,
        )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "operation_id": getattr(record, "operation_id", "-"),
            "event": getattr(record, "event", None),
            "message": record.getMessage(),
        }

        context = {}
        for key, value in record.__dict__.items():
            if key in _STANDARD_KEYS or key in {
                "message",
                "asctime",
                "operation_id",
                "event",
            }:
                continue
            context[key] = sanitize_data(
                value,
                mask_emails=LOG_MASK_EMAILS,
            )

        if context:
            payload["context"] = context
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = sanitize_string(
                record.stack_info,
                mask_emails=LOG_MASK_EMAILS,
            )

        return json.dumps(
            sanitize_data(payload, mask_emails=LOG_MASK_EMAILS),
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )


def _resolve_level(value: str) -> int:
    level = getattr(logging, value, logging.INFO)
    return level if isinstance(level, int) else logging.INFO


def setup_logging(
    *,
    log_format: str | None = None,
    force: bool = True,
) -> logging.Logger:
    """Configure secure console and rotating-file logging."""
    os.makedirs(LOG_DIR, exist_ok=True)

    selected = (
        log_format.strip().lower()
        if log_format is not None
        else LOG_FORMAT
    )
    if selected not in {"text", "json"}:
        selected = "text"

    secure_filter = SecureLogFilter()
    formatter: logging.Formatter
    if selected == "json":
        formatter = JsonLogFormatter()
    else:
        formatter = SecureTextFormatter(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "operation_id=%(operation_id)s | %(message)s"
        )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secure_filter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(secure_filter)

    root_logger = logging.getLogger()
    root_logger.setLevel(_resolve_level(LOG_LEVEL))
    if force:
        root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    return root_logger
