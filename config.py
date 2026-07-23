"""Configuration management for the Workflow Orchestrator.

⚠️ DEPRECATED: This module is a backward-compatibility shim.
Please import from ``workflow_orchestrator.config`` instead.

This module re-exports all symbols from the unified configuration
system at ``workflow_orchestrator/config/config_manager.py``.
"""

from __future__ import annotations

import warnings

from workflow_orchestrator.config.config_manager import (
    ConfigurationManager,
    AppConfig,
    config_manager,
    create_config_manager,
    get_config_manager,
)

__all__ = [
    "ConfigurationManager",
    "AppConfig",
    "config_manager",
    "create_config_manager",
    "get_config_manager",
]

warnings.warn(
    "Deprecated: Import from 'workflow_orchestrator.config' instead of 'config'. "
    "The root 'config.py' is a backward-compatibility shim and will be removed.",
    DeprecationWarning,
    stacklevel=2,
)
