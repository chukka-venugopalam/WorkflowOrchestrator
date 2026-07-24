"""Agent Manager — facade and management for local and remote AI coding agents.

Connects AgentRegistry, AgentRuntime, and AgentDetector.

Supports:
- Claude Code
- Cursor
- VSCode Copilot
- Codex CLI
- OpenCode
- FreeBuff
- Antigravity
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from workflow_orchestrator.intelligence.agent_registry import AgentRegistry, AgentManifest as IntAgentManifest
from workflow_orchestrator.runtime.agent_runtime import AgentRuntime
from workflow_orchestrator.integrations.agent_detector import AgentDetector, DetectedAgent

logger = logging.getLogger(__name__)


@dataclass
class AgentStatusInfo:
    """Detailed status of an AI agent."""

    agent_id: str
    name: str
    installed: bool
    version: str = "unknown"
    workspace: Optional[str] = None
    status: str = "available"
    capabilities: List[str] = field(default_factory=list)
    executable_path: Optional[str] = None


class AgentManager:
    """Discovers, tracks, and launches AI agents."""

    KNOWN_AGENTS = [
        ("claude_code", "Claude Code CLI"),
        ("cursor", "Cursor IDE Agent"),
        ("vscode_copilot", "VSCode GitHub Copilot"),
        ("codex_cli", "OpenAI Codex CLI"),
        ("opencode", "OpenCode Assistant"),
        ("freebuff", "FreeBuff Agent"),
        ("antigravity", "Antigravity Coding Agent"),
    ]

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        runtime: Optional[AgentRuntime] = None,
        detector: Optional[AgentDetector] = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.runtime = runtime or AgentRuntime(agent_registry=self.registry)
        self.detector = detector or AgentDetector()

    def discover_agents(self) -> List[AgentStatusInfo]:
        """Auto-discover all installed AI agents and capabilities."""
        detected = self.detector.detect_all()
        detected_map = {a.agent_id: a for a in detected}

        results: List[AgentStatusInfo] = []

        for aid, name in self.KNOWN_AGENTS:
            det = detected_map.get(aid)
            
            # Retrieve capabilities from registry if registered
            try:
                reg_agent = self.registry.lookup(aid)
                caps = reg_agent.manifest().capabilities
            except Exception:
                caps = ["codegen", "reasoning", "file-edit"]

            info = AgentStatusInfo(
                agent_id=aid,
                name=name,
                installed=det.available if det else False,
                version=det.version if det else "1.0.0",
                workspace=None,
                status="available" if (det and det.available) else "missing",
                capabilities=caps,
                executable_path=det.path if det else None,
            )
            results.append(info)

        return results

    def list_installed(self) -> List[AgentStatusInfo]:
        """Return list of only installed agents."""
        return [a for a in self.discover_agents() if a.installed]

    def get_agent(self, agent_id: str) -> Optional[AgentStatusInfo]:
        """Find agent status by ID."""
        for a in self.discover_agents():
            if a.agent_id.lower() == agent_id.lower():
                return a
        return None
