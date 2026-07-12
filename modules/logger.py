"""Centralized logging configuration for the Workflow Orchestrator.

This module provides a consistent logging setup across the entire
application, with both console and file output handlers.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

# Log format strings
CONSOLE_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
FILE_FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str = "workflow_orchestrator",
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logging.Logger:
    """Configure and return a logger with file and console handlers.

    The logger writes to both the console (INFO and above) and a
    timestamped log file in the logs/ directory.

    Args:
        name: Name of the logger, typically the module name.
        level: Logging level (e.g., logging.DEBUG, logging.INFO).
        log_to_file: Whether to write logs to a file.
        log_to_console: Whether to write logs to the console.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT)

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(console_handler)

    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOG_DIR / f"workflow_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Initialize root logger on import
logger = setup_logger()
