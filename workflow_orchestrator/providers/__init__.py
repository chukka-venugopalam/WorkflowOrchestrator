"""Provider system — abstractions for AI provider configuration and loading.

This package contains the interfaces and configuration models for
provider adapters. No provider implementations exist here.

Contains NO provider-specific code.
Contains NO API calls.
"""

from __future__ import annotations

__all__ = [
    "ProviderManifest",
    "ProviderConfig",
    "ProviderLoader",
]

from workflow_orchestrator.intelligence.models import ProviderManifest


class ProviderConfig:
    """Configuration for a provider adapter.

    Supports loading from dictionaries, environment variables, and config files.
    All configurations are provider-agnostic — provider-specific settings
    are stored in the ``metadata`` field.

    Attributes:
        provider_id: Unique provider identifier.
        api_key_env_var: Name of the environment variable containing the API key.
        base_url: Base URL for the provider API.
        timeout_seconds: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        metadata: Provider-specific configuration.
    """

    def __init__(
        self,
        provider_id: str = "",
        api_key_env_var: str = "",
        base_url: str = "",
        timeout_seconds: int = 120,
        max_retries: int = 3,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.api_key_env_var = api_key_env_var
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.metadata = metadata or {}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProviderConfig:
        """Create from a dictionary.

        Args:
            data: Configuration dictionary.

        Returns:
            A ProviderConfig instance.
        """
        return cls(
            provider_id=data.get("provider_id", data.get("id", "")),
            api_key_env_var=data.get("api_key_env_var", data.get("api_key", "")),
            base_url=data.get("base_url", ""),
            timeout_seconds=data.get("timeout_seconds", 120),
            max_retries=data.get("max_retries", 3),
            metadata={k: v for k, v in data.items()
                      if k not in ("provider_id", "id", "api_key_env_var", "api_key",
                                   "base_url", "timeout_seconds", "max_retries")},
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "provider_id": self.provider_id,
            "api_key_env_var": self.api_key_env_var,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }


class ProviderLoader:
    """Loads provider adapters from configuration.

    This is a foundation stub — it will be extended in future phases
    to support dynamic loading of provider adapter implementations.

    Currently supports:
    - Loading provider configuration from dicts
    - Creating ProviderConfig objects
    - Validating provider configurations
    """

    def __init__(self) -> None:
        self._configs: dict[str, ProviderConfig] = {}

    def load_config(self, config: dict | ProviderConfig) -> ProviderConfig:
        """Load a provider configuration.

        Args:
            config: Provider configuration dict or ProviderConfig.

        Returns:
            A ProviderConfig instance.
        """
        if isinstance(config, ProviderConfig):
            self._configs[config.provider_id] = config
            return config

        provider_config = ProviderConfig.from_dict(config)
        self._configs[provider_config.provider_id] = provider_config
        return provider_config

    def get_config(self, provider_id: str) -> ProviderConfig | None:
        """Get a loaded provider configuration.

        Args:
            provider_id: The provider identifier.

        Returns:
            The ProviderConfig, or None if not found.
        """
        return self._configs.get(provider_id)

    def list_configs(self) -> list[ProviderConfig]:
        """List all loaded provider configurations.

        Returns:
            List of ProviderConfig objects.
        """
        return list(self._configs.values())
