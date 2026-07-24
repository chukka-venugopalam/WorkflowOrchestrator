"""Auto Discovery — automatic system, tool, provider, and environment detection.

Combines EnvironmentDetector, ToolDetector, CliManager, AgentDetector,
ProviderDetector, WorkspaceDetector, and DependencyDetector into a single unified audit.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.integrations.environment_detector import EnvironmentDetector, EnvironmentInfo
from workflow_orchestrator.integrations.tool_detector import ToolDetector, ToolInfo
from workflow_orchestrator.integrations.cli_manager import CliManager, CliToolInfo
from workflow_orchestrator.integrations.agent_detector import AgentDetector, DetectedAgent
from workflow_orchestrator.integrations.provider_detector import ProviderDetector, DetectedProvider
from workflow_orchestrator.integrations.workspace_detector import WorkspaceDetector, WorkspaceInfo
from workflow_orchestrator.integrations.dependency_detector import DependencyDetector, DependencyInfo

logger = logging.getLogger(__name__)


@dataclass
class CompleteDiscoveryAudit:
    """Comprehensive auto-discovery snapshot of the local environment."""

    os_name: str
    python_version: str
    git_installed: bool
    github_cli_installed: bool
    docker_installed: bool
    node_installed: bool
    claude_code_installed: bool
    cursor_installed: bool
    vscode_installed: bool
    codex_cli_installed: bool
    opencode_installed: bool
    render_cli_installed: bool
    vercel_cli_installed: bool
    detected_providers: List[str] = field(default_factory=list)
    detected_agents: List[str] = field(default_factory=list)
    cli_tools: Dict[str, str] = field(default_factory=dict)
    workspace_type: str = "general"


class AutoDiscovery:
    """Auto-discovers environment capabilities and installed software."""

    def __init__(
        self,
        env_detector: Optional[EnvironmentDetector] = None,
        tool_detector: Optional[ToolDetector] = None,
        cli_manager: Optional[CliManager] = None,
        agent_detector: Optional[AgentDetector] = None,
        provider_detector: Optional[ProviderDetector] = None,
        workspace_detector: Optional[WorkspaceDetector] = None,
    ) -> None:
        self.env_detector = env_detector or EnvironmentDetector()
        self.tool_detector = tool_detector or ToolDetector()
        self.cli_manager = cli_manager or CliManager()
        self.agent_detector = agent_detector or AgentDetector()
        self.provider_detector = provider_detector or ProviderDetector()
        self.workspace_detector = workspace_detector or WorkspaceDetector()

    def run_full_discovery(self, target_dir: Optional[str | Path] = None) -> CompleteDiscoveryAudit:
        """Perform a complete auto-discovery audit."""
        env: EnvironmentInfo = self.env_detector.detect()
        cli_tools: List[CliToolInfo] = self.cli_manager.detect_all()
        cli_map = {t.name: t.version for t in cli_tools if t.available}

        agents: List[DetectedAgent] = self.agent_detector.detect_all()
        active_agents = [a.agent_id for a in agents if a.available]

        providers: List[DetectedProvider] = self.provider_detector.detect_all()
        active_providers = [p.provider_id for p in providers if p.available]

        ws_dir = Path(target_dir) if target_dir else Path.cwd()
        ws_info: WorkspaceInfo = self.workspace_detector.detect(ws_dir)

        py_v = env.python_version or f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        return CompleteDiscoveryAudit(
            os_name=env.os_name,
            python_version=py_v,
            git_installed="git" in cli_map,
            github_cli_installed="gh" in cli_map or "github" in cli_map,
            docker_installed="docker" in cli_map,
            node_installed="node" in cli_map or "npm" in cli_map,
            claude_code_installed="claude_code" in active_agents or "claude" in cli_map,
            cursor_installed="cursor" in active_agents or "cursor" in cli_map,
            vscode_installed="vscode" in cli_map or "code" in cli_map,
            codex_cli_installed="codex_cli" in active_agents or "codex" in cli_map,
            opencode_installed="opencode" in active_agents or "opencode" in cli_map,
            render_cli_installed="render" in cli_map,
            vercel_cli_installed="vercel" in cli_map,
            detected_providers=active_providers,
            detected_agents=active_agents,
            cli_tools=cli_map,
            workspace_type=ws_info.type or (ws_info.languages[0] if ws_info.languages else "python"),
        )
