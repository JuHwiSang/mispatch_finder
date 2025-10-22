from __future__ import annotations

import logging
from typing import Any, Dict, Optional


class AnalysisLogger:
    """Structured logger for analysis workflow.

    Provides convenience methods for logging analysis events with payloads.
    Injected via DI to ensure consistent logging across all components.
    """

    def __init__(self, logger_name: str = "mispatch_finder") -> None:
        self._logger = logging.getLogger(logger_name)

    def debug(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message with optional payload."""
        if payload:
            self._logger.debug(message, extra={"payload": payload})
        else:
            self._logger.debug(message)

    def info(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Log info message with optional payload."""
        if payload:
            self._logger.info(message, extra={"payload": payload})
        else:
            self._logger.info(message)

    def warning(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message with optional payload."""
        if payload:
            self._logger.warning(message, extra={"payload": payload})
        else:
            self._logger.warning(message)

    def error(self, message: str, payload: Optional[Dict[str, Any]] = None, exc_info: bool = False) -> None:
        """Log error message with optional payload and exception info."""
        if payload:
            self._logger.error(message, extra={"payload": payload}, exc_info=exc_info)
        else:
            self._logger.error(message, exc_info=exc_info)

    def exception(self, message: str, payload: Optional[Dict[str, Any]] = None) -> None:
        """Log exception with traceback and optional payload."""
        if payload:
            self._logger.exception(message, extra={"payload": payload})
        else:
            self._logger.exception(message)
