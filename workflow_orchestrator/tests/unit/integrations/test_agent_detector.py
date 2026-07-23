"""Tests for AgentDetector integration module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from workflow_orchestrator.integrations.agent_detector import AgentDetector, DetectedAgent


class TestDetectedAgent:
    """Tests for DetectedAgent data class."""

    def test_create(self) -> None:
        agent = DetectedAgent(
            agent_id="claude-code",
            name="Claude Code",
            transport="cli",
            available=True,
        )
        assert agent.agent_id == "claude-code"
        assert agent.name == "Claude Code"
        assert agent.transport == "cli"
        assert agent.available is True

    def test_not_available(self) -> None:
        agent = DetectedAgent(agent_id="test", name="Test")
        assert agent.available is False


class TestAgentDetector:
    """Tests for AgentDetector class."""

    def test_detect_returns_list(self) -> None:
        detector = AgentDetector()
        agents = detector.detect_all()
        assert isinstance(agents, list)

    @patch("shutil.which", return_value="/usr/local/bin/claude")
    def test_detect_claude_code(self, mock_which: MagicMock) -> None:
        detector = AgentDetector()
        agents = detector.detect_all()
        ids = [a.agent_id for a in agents]
        assert "claude-code" in ids

    @patch("shutil.which", return_value="/usr/local/bin/codex")
    def test_detect_codex(self, mock_which: MagicMock) -> None:
        detector = AgentDetector()
        agents = detector.detect_all()
        ids = [a.agent_id for a in agents]
        assert "codex" in ids

    @patch("shutil.which", return_value="/usr/local/bin/cursor")
    def test_detect_cursor(self, mock_which: MagicMock) -> None:
        detector = AgentDetector()
        agents = detector.detect_all()
        ids = [a.agent_id for a in agents]
        assert "cursor" in ids

    def test_no_agents(self) -> None:
        with patch("shutil.which", return_value=None):
            detector = AgentDetector()
            agents = detector.detect_all()
            assert len(agents) == 0

    @patch("shutil.which", return_value="/usr/local/bin/opencode")
    def test_detect_opencode(self, mock_which: MagicMock) -> None:
        detector = AgentDetector()
        agents = detector.detect_all()
        ids = [a.agent_id for a in agents]
        assert "opencode" in ids

    def test_deduplication(self) -> None:
        def which_side_effect(cmd: str) -> Optional[str]:
            return "/usr/local/bin/claude" if cmd == "claude" else None

        with patch("shutil.which", side_effect=which_side_effect):
            detector = AgentDetector()
            agents = detector.detect_all()
            claude_agents = [a for a in agents if a.agent_id == "claude-code"]
            assert len(claude_agents) <= 1
