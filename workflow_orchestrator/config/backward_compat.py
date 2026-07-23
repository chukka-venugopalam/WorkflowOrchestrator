"""Backward compatibility shim for the configuration system.

This module ensures that existing imports from the old ``config`` module
locations still work after the refactoring.  It re-exports all the major
symbols from the new ``workflow_orchestrator.config`` package.

When all code has been updated, this module can be removed in a future
major version.
"""

from __future__ import annotations

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
