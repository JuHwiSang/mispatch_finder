from __future__ import annotations

import logging
from pathlib import Path
from logging import Handler

from .formatters import JSONFormatter, HumanReadableFormatter


def build_json_file_handler(path: Path, level: int = logging.INFO) -> Handler:
    """Create a file handler with JSON formatting.

    Args:
        path: Path to log file (.jsonl)
        level: Logging level

    Returns:
        Configured FileHandler with JSON formatter
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    h = logging.FileHandler(path, encoding="utf-8", mode="a")
    h.setLevel(level)
    h.setFormatter(JSONFormatter())
    return h


def build_human_console_handler(level: int = logging.INFO) -> Handler:
    """Create a console handler with human-readable formatting.

    Args:
        level: Logging level

    Returns:
        Configured StreamHandler with human-readable formatter
    """
    h = logging.StreamHandler()
    h.setLevel(level)
    h.setFormatter(HumanReadableFormatter())
    return h
