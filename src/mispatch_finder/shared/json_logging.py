from __future__ import annotations

import json
import logging
from logging import Handler
from pathlib import Path
from typing import Optional


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        d = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # include structured payload if provided via logging extra
        if hasattr(record, "payload"):
            d["payload"] = record.payload  # type: ignore[attr-defined]
        if record.exc_info:
            d["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(d, ensure_ascii=False)


def build_json_file_handler(path: Path, level: int = logging.INFO) -> Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    h = logging.FileHandler(path, encoding="utf-8", mode="w")
    h.setLevel(level)
    h.setFormatter(JSONFormatter())
    return h


def build_json_console_handler(level: int = logging.INFO) -> Handler:
    h = logging.StreamHandler()
    h.setLevel(level)
    h.setFormatter(JSONFormatter())
    return h
