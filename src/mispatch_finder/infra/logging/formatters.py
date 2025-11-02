from __future__ import annotations

import logging

from pythonjsonlogger.json import JsonFormatter


class JSONFormatter(JsonFormatter):
    """JSON formatter using python-json-logger.

    Formats log records as JSON with support for structured data via extra fields.
    """

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        """Add custom fields to the log record.

        Args:
            log_record: Output dictionary
            record: Python logging record
            message_dict: Message dictionary from format()
        """
        super().add_fields(log_record, record, message_dict)

        # Always include these fields
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['message'] = record.getMessage()

        # Include payload if provided via logging extra
        if hasattr(record, 'payload'):
            log_record['payload'] = record.payload  # type: ignore[attr-defined]


class HumanReadableFormatter(logging.Formatter):
    """Human-readable formatter for console output."""

    def __init__(self) -> None:
        super().__init__(
            fmt='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
