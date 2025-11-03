from __future__ import annotations

import logging
from pathlib import Path

from dependency_injector.resources import Resource

from .handlers import build_json_file_handler, build_human_console_handler


class AnalysisLogger(Resource):
    """Structured logger for analysis workflow.

    Provides convenience methods for logging analysis events with payloads.
    Configured with GHSA-specific log file and optional console output.
    """

    def init(
        self,
        *,
        ghsa: str | None = None,
        logs_dir: Path,
        logger_name: str = "mispatch_finder",
        console_output: bool = False,
        level: str = "INFO",
    ) -> "AnalysisLogger":
        """Initialize logger with optional GHSA-specific configuration.

        Args:
            ghsa: GHSA identifier (optional, if provided creates JSONL file handler)
            logs_dir: Directory to store log files
            logger_name: Logger name
            console_output: Whether to enable console output
            level: Logging level (DEBUG, INFO, WARNING, ERROR)

        Returns:
            Self for dependency_injector Resource pattern
        """
        self._logger = logging.getLogger(logger_name)
        self._logger.setLevel(getattr(logging, level.upper()))
        self._logger.propagate = False  # Don't propagate to root logger

        # Clear existing handlers
        self._logger.handlers.clear()
        self._handlers = []

        # Add file handler only if GHSA is provided
        if ghsa:
            log_file = logs_dir / f"{ghsa}.jsonl"
            file_handler = build_json_file_handler(log_file, level=getattr(logging, level.upper()))
            self._logger.addHandler(file_handler)
            self._handlers.append(file_handler)

        # Optionally add console handler (human-readable format)
        if console_output:
            console_handler = build_human_console_handler(level=getattr(logging, level.upper()))
            self._logger.addHandler(console_handler)
            self._handlers.append(console_handler)

        return self

    def shutdown(self, resource: "AnalysisLogger") -> None:
        """Shutdown logger and close all file handlers.

        This ensures all logs are flushed and file descriptors are released.
        Required for proper cleanup before deleting log files.
        """
        # Flush and close all handlers
        for handler in self._handlers:
            handler.flush()
            handler.close()

        # Remove handlers from logger
        self._logger.handlers.clear()

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with optional extra fields."""
        if kwargs:
            self._logger.debug(message, extra=kwargs)
        else:
            self._logger.debug(message)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with optional extra fields."""
        if kwargs:
            self._logger.info(message, extra=kwargs)
        else:
            self._logger.info(message)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with optional extra fields."""
        if kwargs:
            self._logger.warning(message, extra=kwargs)
        else:
            self._logger.warning(message)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message with optional extra fields and exception info."""
        if kwargs:
            self._logger.error(message, extra=kwargs, exc_info=exc_info)
        else:
            self._logger.error(message, exc_info=exc_info)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback and optional extra fields."""
        if kwargs:
            self._logger.exception(message, extra=kwargs)
        else:
            self._logger.exception(message)
