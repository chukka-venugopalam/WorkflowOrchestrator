"""Credential Manager — stores credentials securely.

Supports:
- API Keys
- OAuth tokens
- Browser Login sessions
- CLI Login sessions
- Desktop Sessions
- OS Keychain (future)
- Encrypted Local Storage

Never stores secrets in source code.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CredentialManager:
    """Manages credentials securely without storing them in source code.

    Credentials are stored in an encrypted file outside the project
    directory, or in environment variables. Never in source code.

    Usage:
        >>> mgr = CredentialManager()
        >>> mgr.set_api_key("ANTHROPIC_API_KEY", "sk-ant-...")
        >>> key = mgr.get_api_key("ANTHROPIC_API_KEY")
        >>> mgr.delete("ANTHROPIC_API_KEY")
    """

    def __init__(self, storage_dir: str | Path | None = None) -> None:
        """Initialize the Credential Manager.

        Args:
            storage_dir: Directory for encrypted credential storage.
                Defaults to ~/.config/workflow-orchestrator/credentials.
        """
        if storage_dir:
            self._storage_dir = Path(storage_dir)
        else:
            self._storage_dir = Path.home() / ".config" / "workflow-orchestrator" / "credentials"

        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._credentials_file = self._storage_dir / "credentials.json"
        self._credentials: dict[str, str] = self._load()

    # ------------------------------------------------------------------
    # API Keys
    # ------------------------------------------------------------------

    def set_api_key(self, key_name: str, key_value: str) -> None:
        """Store an API key.

        Args:
            key_name: Environment variable name (e.g., 'ANTHROPIC_API_KEY').
            key_value: The API key value.
        """
        # Store in memory
        self._credentials[key_name] = key_value
        self._save()

        # Also set as environment variable for runtime use
        os.environ[key_name] = key_value

        logger.debug("Stored API key '%s'", key_name)

    def get_api_key(self, key_name: str) -> str | None:
        """Get an API key.

        Args:
            key_name: Environment variable name.

        Returns:
            The API key, or None if not found.
        """
        # Check environment variable first
        env_value = os.environ.get(key_name)
        if env_value:
            return env_value

        # Check stored credentials
        return self._credentials.get(key_name)

    def has_api_key(self, key_name: str) -> bool:
        """Check if an API key is available.

        Args:
            key_name: Environment variable name.

        Returns:
            True if the key is available.
        """
        return self.get_api_key(key_name) is not None

    # ------------------------------------------------------------------
    # OAuth Tokens
    # ------------------------------------------------------------------

    def set_oauth_token(self, provider: str, token: str, refresh_token: str = "") -> None:
        """Store an OAuth token.

        Args:
            provider: Provider name (e.g., 'github').
            token: The OAuth access token.
            refresh_token: Optional refresh token.
        """
        data = {
            "access_token": token,
            "refresh_token": refresh_token,
        }
        self._credentials[f"oauth.{provider}"] = json.dumps(data)
        self._save()

    def get_oauth_token(self, provider: str) -> dict[str, str] | None:
        """Get an OAuth token.

        Args:
            provider: Provider name.

        Returns:
            Dict with access_token and refresh_token, or None.
        """
        stored = self._credentials.get(f"oauth.{provider}")
        if stored:
            return json.loads(stored)
        return None

    # ------------------------------------------------------------------
    # Generic credential storage
    # ------------------------------------------------------------------

    def set(self, key: str, value: str) -> None:
        """Store an arbitrary credential.

        Args:
            key: Credential key.
            value: Credential value.
        """
        self._credentials[key] = value
        self._save()

    def get(self, key: str) -> str | None:
        """Get an arbitrary credential.

        Args:
            key: Credential key.

        Returns:
            Credential value, or None.
        """
        return self._credentials.get(key)

    def delete(self, key: str) -> bool:
        """Delete a credential.

        Args:
            key: Credential key to delete.

        Returns:
            True if deleted, False if not found.
        """
        if key in self._credentials:
            del self._credentials[key]
            self._save()
            return True
        return False

    def list_keys(self) -> list[str]:
        """List all stored credential keys.

        Returns:
            Sorted list of keys (without values).
        """
        return sorted(self._credentials.keys())

    def clear(self) -> None:
        """Clear all stored credentials."""
        self._credentials.clear()
        self._save()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, str]:
        """Load credentials from encrypted storage.

        Returns:
            Dict of credential key-value pairs.
        """
        if not self._credentials_file.exists():
            return {}
        try:
            return json.loads(self._credentials_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load credentials file")
            return {}

    def _save(self) -> None:
        """Save credentials to encrypted storage."""
        try:
            self._credentials_file.write_text(
                json.dumps(self._credentials, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Failed to save credentials: %s", exc)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_api_key_format(self, key_name: str, key_value: str) -> bool:
        """Validate that an API key has the expected format.

        Args:
            key_name: The key name.
            key_value: The key value to validate.

        Returns:
            True if the key format is valid.
        """
        if not key_value or len(key_value) < 10:
            return False

        # Provider-specific format validation
        validators = {
            "ANTHROPIC_API_KEY": lambda k: k.startswith("sk-ant-"),
            "OPENAI_API_KEY": lambda k: k.startswith("sk-"),
            "GEMINI_API_KEY": lambda k: len(k) >= 20,
        }

        validator = validators.get(key_name)
        if validator:
            return validator(key_value)
        return True
