"""Agent Detector — automatically discovers installed coding agents.

Detects:
Cursor, Claude Code, Codex CLI, OpenCode, Continue, GitHub Copilot
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class DetectedAgent:
    """A coding agent detected on the system.

    Attributes:
        agent_id: Unique agent identifier.
        name: Human-readable name.
        version: Detected version.
        transport: Supported transport.
        path: Path to the agent.
        available: Whether the agent is usable.
    """

    agent_id: str = ""
    name: str = ""
    version: str = ""
    transport: str = ""
    path: str = ""
    available: bool = False


class AgentDetector:
    """Scans the system for installed coding agents.

    Detects agents by checking PATH, standard installation paths,
    and VS Code extensions.

    Usage:
        >>> detector = AgentDetector()
        >>> agents = detector.detect_all()
        >>> for a in agents:
        ...     print(f"{a.name}: {a.transport}")
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Agent Detector.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect_all(self) -> list[DetectedAgent]:
        """Detect all installed coding agents.

        Returns:
            List of DetectedAgent objects.
        """
        agents: list[DetectedAgent] = []
        detectors = [
            self._detect_claude_code,
            self._detect_cursor,
            self._detect_codex,
            self._detect_opencode,
            self._detect_continue,
            self._detect_copilot,
            self._detect_factory,
        ]

        for detector in detectors:
            try:
                agent = detector()
                if agent.available:
                    agents.append(agent)
                    self._publish_event("integration.agent_detected", {
                        "agent_id": agent.agent_id,
                        "transport": agent.transport,
                    })
            except Exception:
                continue

        logger.info("Detected %d coding agents", len(agents))
        return agents

    def _detect_claude_code(self) -> DetectedAgent:
        """Detect Claude Code."""
        path = shutil.which("claude")
        if path:
            return DetectedAgent(
                agent_id="claude-code",
                name="Claude Code",
                transport="cli",
                path=path,
                available=True,
            )
        return DetectedAgent(agent_id="claude-code", name="Claude Code")

    def _detect_cursor(self) -> DetectedAgent:
        """Detect Cursor."""
        path = shutil.which("cursor")
        if path:
            return DetectedAgent(
                agent_id="cursor",
                name="Cursor",
                transport="desktop",
                path=path,
                available=True,
            )
        mac_cursor = Path("/Applications/Cursor.app")
        if mac_cursor.exists():
            return DetectedAgent(
                agent_id="cursor",
                name="Cursor",
                transport="desktop",
                path=str(mac_cursor),
                available=True,
            )
        return DetectedAgent(agent_id="cursor", name="Cursor")

    def _detect_codex(self) -> DetectedAgent:
        """Detect Codex CLI."""
        path = shutil.which("codex")
        if path:
            return DetectedAgent(
                agent_id="codex",
                name="Codex CLI",
                transport="cli",
                path=path,
                available=True,
            )
        return DetectedAgent(agent_id="codex", name="Codex CLI")

    def _detect_opencode(self) -> DetectedAgent:
        """Detect OpenCode."""
        path = shutil.which("opencode")
        if path:
            return DetectedAgent(
                agent_id="opencode",
                name="OpenCode",
                transport="cli",
                path=path,
                available=True,
            )
        return DetectedAgent(agent_id="opencode", name="OpenCode")

    def _detect_continue(self) -> DetectedAgent:
        """Detect Continue.dev."""
        # Check via npm or pip
        path = shutil.which("continue")
        if path:
            return DetectedAgent(
                agent_id="continue",
                name="Continue",
                transport="cli",
                path=path,
                available=True,
            )
        return DetectedAgent(agent_id="continue", name="Continue")

    def _detect_copilot(self) -> DetectedAgent:
        """Detect GitHub Copilot."""
        vscode_extensions = Path.home() / ".vscode" / "extensions"
        if vscode_extensions.exists():
            for ext in vscode_extensions.glob("github.copilot-*"):
                return DetectedAgent(
                    agent_id="github-copilot",
                    name="GitHub Copilot",
                    transport="desktop",
                    path=str(ext),
                    available=True,
                )
        return DetectedAgent(agent_id="github-copilot", name="GitHub Copilot")

    def _detect_factory(self) -> DetectedAgent:
        """Detect Factory AI agent."""
        path = shutil.which("factory")
        if path:
            return DetectedAgent(
                agent_id="factory",
                name="Factory",
                transport="cli",
                path=path,
                available=True,
            )
        return DetectedAgent(agent_id="factory", name="Factory")

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="agent_detector"))
        except Exception:
            pass
