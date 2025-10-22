from __future__ import annotations

import json
import logging


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Formats log records as JSON with optional payload field for structured data.
    """

    def format(self, record: logging.LogRecord) -> str:
        d = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include structured payload if provided via logging extra
        if hasattr(record, "payload"):
            d["payload"] = record.payload  # type: ignore[attr-defined]
        if record.exc_info:
            d["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(d, ensure_ascii=False)
