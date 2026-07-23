"""Tests for ProviderInstaller integration module."""

from __future__ import annotations

from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.provider_installer import ProviderInstaller


class TestProviderInstaller:
    """Tests for ProviderInstaller class."""

    def test_get_install_instructions_claude(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("anthropic.claude")
        assert instructions is not None
        assert "steps" in instructions
        assert "provider_id" in instructions

    def test_get_install_instructions_chatgpt(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("openai.chatgpt")
        assert instructions is not None
        assert len(instructions["steps"]) > 0

    def test_get_install_instructions_gemini(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("google.gemini")
        assert instructions is not None
        assert instructions["env_var"] == "GEMINI_API_KEY"

    def test_get_install_instructions_cursor(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("cursor")
        assert instructions is not None
        assert "website" in instructions

    def test_get_install_instructions_codex(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("codex")
        assert instructions is not None
        assert instructions["verify_command"] is not None

    def test_get_install_instructions_unknown(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("nonexistent.provider")
        assert instructions is not None
        assert "steps" in instructions

    def test_get_install_instructions_short_id(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("claude")
        assert instructions is not None
        assert instructions["provider_id"] == "anthropic.claude"

    def test_verify_installation(self) -> None:
        installer = ProviderInstaller()
        result = installer.verify_installation("anthropic.claude")
        assert isinstance(result, dict)
        assert "installed" in result
        assert "issues" in result

    def test_verify_installation_unknown(self) -> None:
        installer = ProviderInstaller()
        result = installer.verify_installation("unknown.provider")
        assert result["installed"] is False

    def test_get_install_instructions_github_copilot(self) -> None:
        installer = ProviderInstaller()
        instructions = installer.get_install_instructions("github.copilot")
        assert instructions is not None
        assert len(instructions["steps"]) > 0
