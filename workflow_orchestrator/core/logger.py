"""Unified logging system for the Workflow Orchestrator.

Provides a centralized logging system that all components use.
Supports:
- Console logging (with optional Rich formatting)
- File logging (rotating)
- JSON structured logging
- Timestamps with timezone awareness
- Configurable log levels per component
- Correlation IDs for tracing requests across components
- Execution IDs for grouping logs by workflow run
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Context variables for tracing
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
execution_id_var: ContextVar[str] = ContextVar("execution_id", default="")

# Log format strings
SIMPLE_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
DETAILED_FORMAT = (
    "%(asctime)s [%(levelname)-7s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class CorrelationFilter(logging.Filter):
    """Adds correlation ID and execution ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        cid = correlation_id_var.get()
        eid = execution_id_var.get()
        record.correlation_id = cid or "-"
        record.execution_id = eid or "-"
        return True


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "execution_id": getattr(record, "execution_id", "-"),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


class UnifiedLogger:
    """Unified logging interface for the application.

    Provides structured logging with tracing context. All components
    should use this logger instead of direct ``logging.getLogger()``
    calls.

    Usage:
        >>> log = UnifiedLogger.get_logger("my_module")
        >>> log.info("Task started", extra={"task_id": "123"})
        >>> log.with_correlation_id("cid-123").info("Traced message")
    """

    _instances: dict[str, UnifiedLogger] = {}
    _initialized: bool = False

    def __init__(self, name: str, logger: logging.Logger) -> None:
        self._name = name
        self._logger = logger

    @classmethod
    def get_logger(cls, name: str) -> UnifiedLogger:
        """Get a unified logger for the given name.

        Args:
            name: Logger name, typically ``__name__``.

        Returns:
            A UnifiedLogger instance.
        """
        if name in cls._instances:
            return cls._instances[name]

        logger = logging.getLogger(name)
        instance = cls(name, logger)
        cls._instances[name] = instance
        return instance

    @classmethod
    def configure(
        cls,
        level: int | str = logging.INFO,
        log_to_file: bool = True,
        log_to_console: bool = True,
        log_format: str = "detailed",
        log_dir: Path | str | None = None,
        json_logs: bool = False,
        component_levels: dict[str, int | str] | None = None,
    ) -> None:
        """Configure the root logger for the entire application.

        Args:
            level: Default log level.
            log_to_file: Whether to write logs to a file.
            log_to_console: Whether to write logs to the console.
            log_format: ``simple``, ``detailed``, or ``json``.
            log_dir: Directory for log files. Auto-created if not provided.
            json_logs: If True, use JSON formatting for all handlers.
            component_levels: Dict mapping logger names to levels.
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Allow all levels; handlers filter

        # Remove existing handlers
        root_logger.handlers.clear()

        # Add correlation filter
        root_logger.addFilter(CorrelationFilter())

        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)

        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            if json_logs:
                console_handler.setFormatter(JSONFormatter())
            else:
                fmt = DETAILED_FORMAT if log_format == "detailed" else SIMPLE_FORMAT
                console_handler.setFormatter(logging.Formatter(fmt, datefmt=DATE_FORMAT))
            root_logger.addHandler(console_handler)

        # File handler
        if log_to_file:
            log_path = Path(log_dir or Path.cwd() / "logs")
            log_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_path / f"workflow_{timestamp}.log"

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            if json_logs:
                file_handler.setFormatter(JSONFormatter())
            else:
                file_handler.setFormatter(
                    logging.Formatter(DETAILED_FORMAT, datefmt=DATE_FORMAT)
                )
            root_logger.addHandler(file_handler)

        # Set component-specific levels
        if component_levels:
            for comp_name, comp_level in component_levels.items():
                if isinstance(comp_level, str):
                    comp_level = getattr(logging, comp_level.upper(), level)
                logging.getLogger(comp_name).setLevel(comp_level)

        cls._initialized = True

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    @staticmethod
    def set_correlation_id(cid: str) -> None:
        """Set the correlation ID for the current context.

        Args:
            cid: The correlation ID string.
        """
        correlation_id_var.set(cid)

    @staticmethod
    def set_execution_id(eid: str) -> None:
        """Set the execution ID for the current context.

        Args:
            eid: The execution ID string.
        """
        execution_id_var.set(eid)

    @staticmethod
    def get_correlation_id() -> str:
        """Get the current correlation ID.

        Returns:
            The correlation ID, or empty string if not set.
        """
        return correlation_id_var.get()

    @staticmethod
    def get_execution_id() -> str:
        """Get the current execution ID.

        Returns:
            The execution ID, or empty string if not set.
        """
        return execution_id_var.get()

    @staticmethod
    def new_correlation_id() -> str:
        """Generate and set a new correlation ID.

        Returns:
            The new correlation ID.
        """
        cid = uuid.uuid4().hex[:12]
        correlation_id_var.set(cid)
        return cid

    @staticmethod
    def new_execution_id() -> str:
        """Generate and set a new execution ID.

        Returns:
            The new execution ID.
        """
        eid = uuid.uuid4().hex[:12]
        execution_id_var.set(eid)
        return eid

    def with_correlation_id(self, cid: str) -> UnifiedLogger:
        """Return a logger bound to a specific correlation ID.

        Args:
            cid: The correlation ID.

        Returns:
            Self (correlation ID is set on context var).
        """
        correlation_id_var.set(cid)
        return self

    def with_execution_id(self, eid: str) -> UnifiedLogger:
        """Return a logger bound to a specific execution ID.

        Args:
            eid: The execution ID.

        Returns:
            Self (execution ID is set on context var).
        """
        execution_id_var.set(eid)
        return self

    # ------------------------------------------------------------------
    # Logging methods
    # ------------------------------------------------------------------

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a DEBUG message."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an INFO message."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a WARNING message."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an ERROR message."""
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a CRITICAL message."""
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an ERROR with exception info."""
        self._logger.exception(msg, *args, **kwargs)

    @property
    def name(self) -> str:
        """The logger name."""
        return self._name

    @property
    def logger(self) -> logging.Logger:
        """The underlying standard library logger."""
        return self._logger


# Module-level convenience functions

def get_logger(name: str) -> UnifiedLogger:
    """Get a unified logger for the given name.

    Args:
        name: Logger name, typically ``__name__``.

    Returns:
        A UnifiedLogger instance.
    """
    return UnifiedLogger.get_logger(name)


def configure_logging(
    level: int | str = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_format: str = "detailed",
    json_logs: bool = False,
    log_dir: Path | str | None = None,
    component_levels: dict[str, int | str] | None = None,
) -> None:
    """Configure the root logger for the application.

    Args:
        level: Default log level (e.g., ``logging.INFO`` or ``\"INFO\"``).
        log_to_file: Whether to write logs to a file.
        log_to_console: Whether to write logs to the console.
        log_format: ``simple``, ``detailed``, or ``json``.
        json_logs: If True, use JSON formatting.
        log_dir: Directory for log files.
        component_levels: Dict mapping logger names to levels.
    """
    UnifiedLogger.configure(
        level=level,
        log_to_file=log_to_file,
        log_to_console=log_to_console,
        log_format=log_format,
        log_dir=log_dir,
        json_logs=json_logs,
        component_levels=component_levels,
    )


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current context."""
    UnifiedLogger.set_correlation_id(cid)


def set_execution_id(eid: str) -> None:
    """Set the execution ID for the current context."""
    UnifiedLogger.set_execution_id(eid)


def new_correlation_id() -> str:
    """Generate and set a new correlation ID."""
    return UnifiedLogger.new_correlation_id()


def new_execution_id() -> str:
    """Generate and set a new execution ID."""
    return UnifiedLogger.new_execution_id()
