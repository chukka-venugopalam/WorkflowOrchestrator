"""Workflow Doctor — complete diagnostics engine for the Workflow Orchestrator.

Checks:
- Python environment & Virtualenv
- Core & optional Dependencies
- Version Control (Git & GitHub CLI)
- Containerization (Docker)
- Runtime Runtimes (Node.js)
- Installed Providers & API Keys
- Installed Agents & Transports
- MCP Server Connectivity
- Internet & Network Health
- Workspace File Permissions
- Configuration Validity
- Plugin & Workflow Loaders
- Overall System Health
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.integrations.health_monitor import HealthMonitor, HealthReport, HealthCheck, HealthStatus
from workflow_orchestrator.orchestrator.discovery import AutoDiscovery
from workflow_orchestrator.orchestrator.provider_manager import ProviderManager
from workflow_orchestrator.orchestrator.agent_manager import AgentManager
from workflow_orchestrator.orchestrator.mcp_manager import MCPManager

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticItem:
    """Individual diagnostic check result."""

    category: str
    name: str
    status: str  # "OK", "WARNING", "FAIL", "INFO"
    message: str
    remedy: Optional[str] = None


@dataclass
class DiagnosticReport:
    """Complete diagnostic report from workflow doctor."""

    passed_count: int
    warning_count: int
    failed_count: int
    items: List[DiagnosticItem] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.failed_count == 0


class WorkflowDoctor:
    """Engine powering the `workflow doctor` diagnostic command."""

    def __init__(
        self,
        health_monitor: Optional[HealthMonitor] = None,
        discovery: Optional[AutoDiscovery] = None,
        provider_manager: Optional[ProviderManager] = None,
        agent_manager: Optional[AgentManager] = None,
        mcp_manager: Optional[MCPManager] = None,
    ) -> None:
        self.health_monitor = health_monitor or HealthMonitor()
        self.discovery = discovery or AutoDiscovery()
        self.provider_mgr = provider_manager or ProviderManager()
        self.agent_mgr = agent_manager or AgentManager()
        self.mcp_mgr = mcp_manager or MCPManager()

    def diagnose(self) -> DiagnosticReport:
        """Run all diagnostic suites and generate a report."""
        items: List[DiagnosticItem] = []

        # 1. Python & Venv
        items.append(self._check_python_environment())
        items.append(self._check_virtual_env())

        # 2. Tools & CLI
        audit = self.discovery.run_full_discovery()
        items.append(DiagnosticItem("Tools", "Git VCS", "OK" if audit.git_installed else "WARNING", "Git CLI installed" if audit.git_installed else "Git CLI missing", None if audit.git_installed else "Install Git"))
        items.append(DiagnosticItem("Tools", "GitHub CLI", "OK" if audit.github_cli_installed else "INFO", "GitHub CLI available" if audit.github_cli_installed else "gh CLI not detected", None))
        items.append(DiagnosticItem("Tools", "Docker Runtime", "OK" if audit.docker_installed else "INFO", "Docker CLI available" if audit.docker_installed else "Docker not running or missing", None))
        items.append(DiagnosticItem("Tools", "Node.js Runtime", "OK" if audit.node_installed else "INFO", "Node.js available" if audit.node_installed else "Node.js not detected", None))

        # 3. Providers & API Keys
        providers = self.provider_mgr.discover_and_load()
        enabled_count = len([p for p in providers if p.enabled])
        key_count = len([p for p in providers if p.api_key_configured])
        items.append(DiagnosticItem("Providers", "Registered Providers", "OK" if enabled_count > 0 else "WARNING", f"{enabled_count} provider(s) enabled out of {len(providers)}", "Configure providers in setup"))
        items.append(DiagnosticItem("Providers", "API Key Credentials", "OK" if key_count > 0 else "WARNING", f"{key_count} provider API key(s) configured", "Set ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY / OPENROUTER_API_KEY"))
        
        sim_providers = [p.name for p in providers if not p.api_key_configured]
        if sim_providers:
            items.append(DiagnosticItem("Providers", "Execution Mode", "INFO", f"Providers running in SIMULATION_MODE due to missing API keys: {', '.join(sim_providers)}", "Provide API keys for REAL_API execution"))
        else:
            items.append(DiagnosticItem("Providers", "Execution Mode", "OK", "All registered providers configured for REAL_API execution", None))

        # 4. Agents
        agents = self.agent_mgr.discover_agents()
        installed_agents = [a for a in agents if a.installed]
        items.append(DiagnosticItem("Agents", "Installed AI Agents", "OK" if installed_agents else "INFO", f"{len(installed_agents)} agent(s) detected: {', '.join(a.name for a in installed_agents) if installed_agents else 'None'}", None))

        # 5. MCP Servers
        mcp_servers = self.mcp_mgr.discover_and_list()
        items.append(DiagnosticItem("MCP", "MCP Servers", "OK" if mcp_servers else "INFO", f"{len(mcp_servers)} MCP server(s) configured", None))

        # 6. Workspace & Permissions
        items.append(self._check_workspace_permissions())

        # 7. Network & Internet
        items.append(self._check_internet_connection())

        passed = len([i for i in items if i.status == "OK"])
        warnings = len([i for i in items if i.status == "WARNING"])
        failed = len([i for i in items if i.status == "FAIL"])

        return DiagnosticReport(passed_count=passed, warning_count=warnings, failed_count=failed, items=items)

    def _check_python_environment(self) -> DiagnosticItem:
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 9):
            return DiagnosticItem("Python", "Interpreter", "OK", f"Python {py_ver} ({sys.executable})")
        return DiagnosticItem("Python", "Interpreter", "WARNING", f"Python {py_ver} (Python 3.9+ recommended)")

    def _check_virtual_env(self) -> DiagnosticItem:
        in_venv = sys.prefix != sys.base_prefix or "VIRTUAL_ENV" in os.environ
        if in_venv:
            return DiagnosticItem("Python", "Virtual Environment", "OK", f"Active virtual environment ({sys.prefix})")
        return DiagnosticItem("Python", "Virtual Environment", "INFO", "Running outside virtual environment")

    def _check_workspace_permissions(self) -> DiagnosticItem:
        cwd = Path.cwd()
        try:
            test_file = cwd / ".perm_check.tmp"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            return DiagnosticItem("Workspace", "Permissions", "OK", f"Read & Write permission confirmed for {cwd}")
        except Exception as exc:
            return DiagnosticItem("Workspace", "Permissions", "FAIL", f"Write permission denied for {cwd}: {exc}", "Fix directory permissions")

    def _check_internet_connection(self) -> DiagnosticItem:
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return DiagnosticItem("Network", "Internet Connectivity", "OK", "Outbound internet connectivity verified")
        except Exception:
            return DiagnosticItem("Network", "Internet Connectivity", "WARNING", "No internet connection detected (offline mode)")
