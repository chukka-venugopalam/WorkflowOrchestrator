"""Provider Configuration — creates and manages provider YAML configuration files.

Each provider stores:
name, transport, priority, quality, cost, timeouts, retry,
authentication, capabilities, limits, workspace, environment
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class ProviderConfiguration:
    """Creates and manages provider YAML configuration files.

    Supports reading, writing, validating, and migrating provider
    configuration stored as YAML files in a configurable directory.

    Usage:
        >>> config = ProviderConfiguration(config_dir="providers/yaml")
        >>> cfg = config.read("claude")
        >>> config.write("claude", cfg)
    """

    # Default provider configurations
    _DEFAULT_CONFIGS: dict[str, dict[str, Any]] = {
        "claude": {
            "name": "Claude",
            "provider_id": "anthropic.claude",
            "transport": "rest_api",
            "priority": 10,
            "quality": "high",
            "cost": "medium",
            "timeouts": {
                "connect": 30,
                "read": 120,
                "write": 120,
            },
            "retry": {
                "max_retries": 3,
                "delay": 2.0,
                "backoff": 2.0,
            },
            "authentication": {
                "method": "api_key",
                "env_var": "ANTHROPIC_API_KEY",
            },
            "capabilities": [
                "reasoning.code-review",
                "reasoning.architecture",
                "codegen.implementation",
                "codegen.nextjs",
                "codegen.python-api",
                "verify.testing",
                "verify.lint",
                "tool.terminal",
            ],
            "limits": {
                "max_tokens": 4096,
                "max_concurrent": 5,
                "rate_limit": 50,
            },
            "workspace": {
                "sandbox": False,
                "max_file_size_mb": 10,
            },
            "environment": {
                "required_vars": ["ANTHROPIC_API_KEY"],
            },
        },
        "chatgpt": {
            "name": "ChatGPT",
            "provider_id": "openai.chatgpt",
            "transport": "rest_api",
            "priority": 20,
            "quality": "high",
            "cost": "medium",
            "timeouts": {
                "connect": 30,
                "read": 120,
                "write": 120,
            },
            "retry": {
                "max_retries": 3,
                "delay": 2.0,
                "backoff": 2.0,
            },
            "authentication": {
                "method": "api_key",
                "env_var": "OPENAI_API_KEY",
            },
            "capabilities": [
                "reasoning.code-review",
                "reasoning.architecture",
                "codegen.implementation",
                "verify.testing",
            ],
            "limits": {
                "max_tokens": 4096,
                "max_concurrent": 5,
                "rate_limit": 500,
            },
            "workspace": {
                "sandbox": False,
                "max_file_size_mb": 10,
            },
            "environment": {
                "required_vars": ["OPENAI_API_KEY"],
            },
        },
        "gemini": {
            "name": "Gemini",
            "provider_id": "google.gemini",
            "transport": "rest_api",
            "priority": 30,
            "quality": "high",
            "cost": "low",
            "timeouts": {
                "connect": 30,
                "read": 120,
                "write": 120,
            },
            "retry": {
                "max_retries": 3,
                "delay": 2.0,
                "backoff": 2.0,
            },
            "authentication": {
                "method": "api_key",
                "env_var": "GEMINI_API_KEY",
            },
            "capabilities": [
                "reasoning.code-review",
                "codegen.implementation",
            ],
            "limits": {
                "max_tokens": 8192,
                "max_concurrent": 3,
                "rate_limit": 60,
            },
            "workspace": {
                "sandbox": False,
                "max_file_size_mb": 10,
            },
            "environment": {
                "required_vars": ["GEMINI_API_KEY"],
            },
        },
        "cursor": {
            "name": "Cursor",
            "provider_id": "cursor",
            "transport": "desktop",
            "priority": 40,
            "quality": "high",
            "cost": "low",
            "timeouts": {"connect": 60, "read": 300, "write": 300},
            "retry": {"max_retries": 2, "delay": 5.0, "backoff": 2.0},
            "authentication": {"method": "desktop_session"},
            "capabilities": ["codegen.implementation", "reasoning.code-review", "tool.filesystem"],
            "limits": {"max_tokens": 16384, "max_concurrent": 1},
            "workspace": {"sandbox": True, "max_file_size_mb": 50},
            "environment": {"required_vars": []},
        },
        "copilot": {
            "name": "GitHub Copilot",
            "provider_id": "github.copilot",
            "transport": "desktop",
            "priority": 50,
            "quality": "medium",
            "cost": "low",
            "timeouts": {"connect": 30, "read": 60, "write": 60},
            "retry": {"max_retries": 2, "delay": 3.0, "backoff": 2.0},
            "authentication": {"method": "oauth", "provider": "github"},
            "capabilities": ["codegen.implementation", "reasoning.code-review"],
            "limits": {"max_tokens": 2048, "max_concurrent": 1},
            "workspace": {"sandbox": False, "max_file_size_mb": 5},
            "environment": {"required_vars": []},
        },
        "codex": {
            "name": "Codex CLI",
            "provider_id": "codex",
            "transport": "cli",
            "priority": 35,
            "quality": "high",
            "cost": "medium",
            "timeouts": {"connect": 30, "read": 180, "write": 180},
            "retry": {"max_retries": 2, "delay": 3.0, "backoff": 2.0},
            "authentication": {"method": "api_key", "env_var": "OPENAI_API_KEY"},
            "capabilities": ["codegen.implementation", "codegen.python-api"],
            "limits": {"max_tokens": 8192, "max_concurrent": 1},
            "workspace": {"sandbox": True, "max_file_size_mb": 20},
            "environment": {"required_vars": ["OPENAI_API_KEY"]},
        },
    }

    def __init__(self, config_dir: str | Path = "providers/yaml") -> None:
        """Initialize the Provider Configuration manager.

        Args:
            config_dir: Directory for YAML configuration files.
        """
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def read(self, name: str) -> dict[str, Any] | None:
        """Read a provider configuration by name.

        Args:
            name: Provider name (e.g., "claude", "chatgpt").

        Returns:
            Configuration dict, or None if not found.
        """
        yaml_path = self._config_dir / f"{name}.yaml"
        if not yaml_path.exists():
            return None
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def write(self, name: str, config: dict[str, Any]) -> Path:
        """Write a provider configuration to disk.

        Args:
            name: Provider name.
            config: Configuration dict.

        Returns:
            Path to the written file.
        """
        yaml_path = self._config_dir / f"{name}.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
        logger.debug("Wrote provider config: %s", yaml_path)
        return yaml_path

    def get_default(self, name: str) -> dict[str, Any] | None:
        """Get the default configuration for a provider.

        Args:
            name: Provider name.

        Returns:
            Default configuration dict, or None.
        """
        return self._DEFAULT_CONFIGS.get(name)

    def create_default(self, name: str) -> dict[str, Any] | None:
        """Create a default configuration file for a provider.

        Args:
            name: Provider name.

        Returns:
            The created configuration dict, or None.
        """
        config = self.get_default(name)
        if config is None:
            return None
        self.write(name, config)
        return config

    def create_all_defaults(self) -> list[str]:
        """Create default configurations for all known providers.

        Returns:
            List of created configuration names.
        """
        created: list[str] = []
        for name in self._DEFAULT_CONFIGS:
            if not (self._config_dir / f"{name}.yaml").exists():
                self.create_default(name)
                created.append(name)
        return created

    def list_configs(self) -> list[str]:
        """List available provider configuration names.

        Returns:
            Sorted list of configuration names.
        """
        return sorted(
            p.stem for p in self._config_dir.glob("*.yaml")
        )

    def validate(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate a provider configuration.

        Args:
            config: Configuration dict to validate.

        Returns:
            Dict with validation results.
        """
        required_fields = ["name", "provider_id", "transport"]
        issues: list[str] = []

        for field in required_fields:
            if field not in config:
                issues.append(f"Missing required field: {field}")

        valid_transports = ["rest_api", "cli", "browser", "desktop", "ssh", "mcp"]
        if "transport" in config and config["transport"] not in valid_transports:
            issues.append(f"Invalid transport: {config['transport']}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "field_count": len(config),
        }

    def to_json(self, config: dict[str, Any]) -> str:
        """Convert configuration to JSON string.

        Args:
            config: Configuration dict.

        Returns:
            JSON string.
        """
        return json.dumps(config, indent=2, default=str)
