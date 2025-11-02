from __future__ import annotations

import logging
from pathlib import Path

from .handlers import build_json_file_handler, build_human_console_handler


class AnalysisLogger:
    """Structured logger for analysis workflow.

    Provides convenience methods for logging analysis events with payloads.
    Configured with GHSA-specific log file and optional console output.
    """

    def __init__(
        self,
        *,
        ghsa: str,
        logs_dir: Path,
        logger_name: str = "mispatch_finder",
        console_output: bool = False,
        level: str = "INFO",
    ) -> None:
        """Initialize logger with GHSA-specific configuration.

        Args:
            ghsa: GHSA identifier (required for log file naming)
            logs_dir: Directory to store log files
            logger_name: Logger name
            console_output: Whether to enable console output
            level: Logging level (DEBUG, INFO, WARNING, ERROR)

        Raises:
            ValueError: If ghsa is not provided
        """
        if not ghsa:
            raise ValueError("ghsa is required for AnalysisLogger initialization")

        self._logger = logging.getLogger(f"{logger_name}.{ghsa}")
        self._logger.setLevel(getattr(logging, level.upper()))
        self._logger.propagate = False  # Don't propagate to root logger

        # Clear existing handlers
        self._logger.handlers.clear()

        # Always add file handler (JSONL format)
        log_file = logs_dir / f"{ghsa}.jsonl"
        file_handler = build_json_file_handler(log_file, level=getattr(logging, level.upper()))
        self._logger.addHandler(file_handler)

        # Optionally add console handler (human-readable format)
        if console_output:
            console_handler = build_human_console_handler(level=getattr(logging, level.upper()))
            self._logger.addHandler(console_handler)

    def debug(self, message: str, payload: dict | None = None) -> None:
        """Log debug message with optional payload."""
        if payload:
            self._logger.debug(message, extra={"payload": payload})
        else:
            self._logger.debug(message)

    def info(self, message: str, payload: dict | None = None) -> None:
        """Log info message with optional payload."""
        if payload:
            self._logger.info(message, extra={"payload": payload})
        else:
            self._logger.info(message)

    def warning(self, message: str, payload: dict | None = None) -> None:
        """Log warning message with optional payload."""
        if payload:
            self._logger.warning(message, extra={"payload": payload})
        else:
            self._logger.warning(message)

    def error(self, message: str, payload: dict | None = None, exc_info: bool = False) -> None:
        """Log error message with optional payload and exception info."""
        if payload:
            self._logger.error(message, extra={"payload": payload}, exc_info=exc_info)
        else:
            self._logger.error(message, exc_info=exc_info)

    def exception(self, message: str, payload: dict | None = None) -> None:
        """Log exception with traceback and optional payload."""
        if payload:
            self._logger.exception(message, extra={"payload": payload})
        else:
            self._logger.exception(message)
