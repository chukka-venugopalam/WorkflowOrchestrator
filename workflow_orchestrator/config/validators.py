"""Configuration validators for the Workflow Orchestrator.

Provides validation functions for configuration values, including
type checking, range validation, and schema validation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from workflow_orchestrator.config.settings import KNOWN_CONFIG_KEYS


class ConfigValidationError(ValueError):
    """Raised when a configuration value fails validation."""

    pass


def validate_key(key: str, value: Any) -> None:
    """Validate a configuration key-value pair.

    Args:
        key: The configuration key.
        value: The value to validate.

    Raises:
        ConfigValidationError: If validation fails.
    """
    if key not in KNOWN_CONFIG_KEYS:
        raise ConfigValidationError(f"Unknown configuration key: '{key}'")

    expected_type = KNOWN_CONFIG_KEYS[key]
    if not isinstance(value, expected_type):
        raise ConfigValidationError(
            f"Invalid type for '{key}': expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )

    # Additional validation for specific keys
    if key == "log_level" and value not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        raise ConfigValidationError(
            f"Invalid log level '{value}'. Must be one of: "
            "DEBUG, INFO, WARNING, ERROR, CRITICAL"
        )

    if key == "default_timeout" and value < 0:
        raise ConfigValidationError(f"default_timeout must be >= 0, got {value}")

    if key == "max_retries" and value < 0:
        raise ConfigValidationError(f"max_retries must be >= 0, got {value}")

    if key == "retry_delay" and value < 0:
        raise ConfigValidationError(f"retry_delay must be >= 0, got {value}")


def validate_profile_name(name: str) -> bool:
    """Validate a profile name.

    Args:
        name: The profile name to validate.

    Returns:
        True if valid.
    """
    if not name or not name.strip():
        return False
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return False
    return True


def validate_url(url: str) -> bool:
    """Basic URL validation.

    Args:
        url: The URL string to validate.

    Returns:
        True if the URL looks valid.
    """
    if not url:
        return True  # Empty URLs are allowed
    return url.startswith(("http://", "https://"))
