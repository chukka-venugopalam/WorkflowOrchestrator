"""Provider Installer — guides users through provider installation.

When a provider is detected as missing, this module produces:
- Installation instructions
- Verification commands
- Post-install setup steps
"""

from __future__ import annotations

import logging
import shutil
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ProviderInstaller:
    """Guides users through installing missing providers.

    Provides platform-specific installation instructions and
    verifies successful installation after setup.

    Usage:
        >>> installer = ProviderInstaller()
        >>> instructions = installer.get_install_instructions("anthropic.claude")
        >>> print(instructions["steps"][0])
    """

    # Installation instructions for each provider
    _INSTALL_GUIDES: dict[str, dict[str, Any]] = {
        "anthropic.claude": {
            "name": "Claude (Anthropic)",
            "website": "https://console.anthropic.com/",
            "api_key_url": "https://console.anthropic.com/keys",
            "steps": [
                "1. Visit https://console.anthropic.com/ to create an account",
                "2. Generate an API key from https://console.anthropic.com/keys",
                "3. Set the ANTHROPIC_API_KEY environment variable",
                "4. For Claude Code CLI: pip install claude-code or npm install -g @anthropic/claude-code",
            ],
            "env_var": "ANTHROPIC_API_KEY",
            "verify_command": "echo $ANTHROPIC_API_KEY",
            "post_install": ["Set ANTHROPIC_API_KEY in your shell profile"],
        },
        "openai.chatgpt": {
            "name": "ChatGPT (OpenAI)",
            "website": "https://platform.openai.com/",
            "api_key_url": "https://platform.openai.com/api-keys",
            "steps": [
                "1. Visit https://platform.openai.com/ to create an account",
                "2. Generate an API key from https://platform.openai.com/api-keys",
                "3. Set the OPENAI_API_KEY environment variable",
            ],
            "env_var": "OPENAI_API_KEY",
            "verify_command": "echo $OPENAI_API_KEY",
            "post_install": ["Set OPENAI_API_KEY in your shell profile"],
        },
        "google.gemini": {
            "name": "Gemini (Google)",
            "website": "https://ai.google.dev/",
            "api_key_url": "https://aistudio.google.com/apikey",
            "steps": [
                "1. Visit https://aistudio.google.com/ to get an API key",
                "2. Set the GEMINI_API_KEY environment variable",
                "3. For Gemini CLI: npm install -g @google/gemini",
            ],
            "env_var": "GEMINI_API_KEY",
            "verify_command": "echo $GEMINI_API_KEY",
            "post_install": ["Set GEMINI_API_KEY in your shell profile"],
        },
        "cursor": {
            "name": "Cursor Editor",
            "website": "https://cursor.sh/",
            "api_key_url": "",
            "steps": [
                "1. Download Cursor from https://cursor.sh/",
                "2. Install the application",
                "3. Launch Cursor and sign in with your account",
            ],
            "env_var": "",
            "verify_command": "which cursor || test -d '/Applications/Cursor.app'",
            "post_install": ["Launch Cursor and configure AI provider settings"],
        },
        "codex": {
            "name": "Codex CLI",
            "website": "https://github.com/openai/codex",
            "api_key_url": "https://platform.openai.com/api-keys",
            "steps": [
                "1. Install Codex CLI: npm install -g @openai/codex",
                "2. Set OPENAI_API_KEY environment variable",
            ],
            "env_var": "OPENAI_API_KEY",
            "verify_command": "codex --version",
            "post_install": ["Verify installation with 'codex --version'"],
        },
        "github.copilot": {
            "name": "GitHub Copilot",
            "website": "https://github.com/features/copilot",
            "api_key_url": "",
            "steps": [
                "1. Install VS Code extension: GitHub Copilot",
                "2. Sign in with your GitHub account",
                "3. Enable Copilot in VS Code settings",
            ],
            "env_var": "",
            "verify_command": "ls ~/.vscode/extensions/github.copilot-*",
            "post_install": ["Restart VS Code after installing the extension"],
        },
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Provider Installer.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def get_install_instructions(self, provider_id: str) -> dict[str, Any]:
        """Get installation instructions for a provider.

        Args:
            provider_id: The provider identifier.

        Returns:
            Dict with installation instructions.
        """
        provider_id = self._resolve_id(provider_id)
        guide = self._INSTALL_GUIDES.get(provider_id, {
            "name": provider_id,
            "steps": [f"See the provider's documentation for installation instructions"],
            "verify_command": "",
            "post_install": [],
        })
        return {**guide, "provider_id": provider_id}

    def verify_installation(self, provider_id: str) -> dict[str, Any]:
        """Verify that a provider is installed correctly.

        Args:
            provider_id: The provider identifier.

        Returns:
            Dict with verification results.
        """
        provider_id = self._resolve_id(provider_id)
        guide = self._INSTALL_GUIDES.get(provider_id)

        if guide is None:
            return {"installed": False, "error": f"Unknown provider: {provider_id}"}

        env_var = guide.get("env_var", "")
        verify_cmd = guide.get("verify_command", "")

        installed = False
        issues: list[str] = []

        # Check environment variable
        if env_var:
            import os
            if os.environ.get(env_var):
                installed = True
            else:
                issues.append(f"Environment variable {env_var} is not set")

        # Check command availability
        if verify_cmd:
            command = verify_cmd.split()[0]
            if shutil.which(command):
                installed = True
            else:
                issues.append(f"Command '{command}' not found in PATH")

        return {
            "installed": installed,
            "provider_id": provider_id,
            "env_var_set": bool(env_var and __import__("os").environ.get(env_var)) if env_var else None,
            "command_found": bool(shutil.which(verify_cmd.split()[0])) if verify_cmd else None,
            "issues": issues,
            "next_steps": guide.get("steps", []) if not installed else guide.get("post_install", []),
        }

    def _resolve_id(self, provider_id: str) -> str:
        """Resolve a short provider ID to its full ID."""
        short_map = {
            "claude": "anthropic.claude",
            "chatgpt": "openai.chatgpt", "gpt": "openai.chatgpt",
            "gemini": "google.gemini",
        }
        return short_map.get(provider_id.lower(), provider_id)
