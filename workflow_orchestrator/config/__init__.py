"""Configuration system for the Workflow Orchestrator.

Provides a unified configuration system that supports:
- JSON config files (``data/config.json``)
- YAML profile files (``profiles/*.yaml``)
- Environment variable overrides
- Profile merging and validation
- Configuration caching

The system merges configuration from multiple sources with
the following precedence (lowest to highest):
    Built-in defaults < Global user config < Project config
    < Environment overrides < CLI flags
"""

from __future__ import annotations

from workflow_orchestrator.config.config_manager import (
    ConfigurationManager,
    AppConfig,
    create_config_manager,
    get_config_manager,
)

__all__ = [
    "ConfigurationManager",
    "AppConfig",
    "create_config_manager",
    "get_config_manager",
]
