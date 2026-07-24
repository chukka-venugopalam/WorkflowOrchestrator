"""Master Orchestrator — Single Entry Point for the Workflow Orchestrator AI Operating System.

Wires together all existing subsystems through dependency injection:
- Core Kernel & Event Bus
- Configuration & Profiles
- Capability Registry & Service Registry
- Workspace & Artifact Managers
- Intelligence & Decision Engine
- Context Engine & Knowledge System
- Project Contracts & Session Runtime
- Runtime Layer (Provider, Agent, Transport)
- Execution Engine & Builder
- Integrations & Auto-Discovery
- Doctor Diagnostics & Self Healing
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.core.kernel import Kernel
from workflow_orchestrator.core.event_bus import EventBus
from workflow_orchestrator.config.config_manager import ConfigurationManager
from workflow_orchestrator.orchestrator.boot import BootSequence, BootReport
from workflow_orchestrator.orchestrator.provider_manager import ProviderManager
from workflow_orchestrator.orchestrator.transport_manager import TransportManager
from workflow_orchestrator.orchestrator.agent_manager import AgentManager
from workflow_orchestrator.orchestrator.mcp_manager import MCPManager
from workflow_orchestrator.orchestrator.discovery import AutoDiscovery, CompleteDiscoveryAudit
from workflow_orchestrator.orchestrator.doctor import WorkflowDoctor, DiagnosticReport
from workflow_orchestrator.orchestrator.first_run import SetupWizard, SetupConfiguration
from workflow_orchestrator.orchestrator.project_flow import ProjectFlowEngine, FlowExecutionRecord
from workflow_orchestrator.orchestrator.self_healing import SelfHealingEngine
from workflow_orchestrator.orchestrator.dashboard import StartupDashboard, ProjectDashboard

logger = logging.getLogger(__name__)


class Orchestrator:
    """The master AI Operating System Orchestrator facade."""

    _instance: Optional["Orchestrator"] = None

    def __init__(self, kernel: Optional[Kernel] = None) -> None:
        self.kernel = kernel or Kernel.create_default()
        self.boot_sequence = BootSequence(kernel=self.kernel)

        # Managers & Engines (initialized after boot or dynamically)
        self.provider_manager = ProviderManager()
        self.transport_manager = TransportManager()
        self.agent_manager = AgentManager()
        self.mcp_manager = MCPManager()
        self.auto_discovery = AutoDiscovery()
        self.doctor = WorkflowDoctor()
        self.setup_wizard = SetupWizard()
        self.project_flow = ProjectFlowEngine()
        self.self_healing = SelfHealingEngine()

    @classmethod
    def get_instance(cls) -> "Orchestrator":
        """Singleton accessor for global Orchestrator instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def boot(self, show_dashboard: bool = True) -> BootReport:
        """Run the 14-step boot sequence and wire up all services."""
        report = self.boot_sequence.execute(show_dashboard=show_dashboard)
        
        # Wire kernel services if booted successfully
        if report.success:
            event_bus = self.kernel.get_service("event_bus") if self.kernel.registry.has_service("event_bus") else None
            self.project_flow = ProjectFlowEngine(event_bus=event_bus)
            self.self_healing = SelfHealingEngine(event_bus=event_bus)

        return report

    def run_doctor(self) -> DiagnosticReport:
        """Execute complete system diagnostics."""
        return self.doctor.diagnose()

    def run_setup(self, setup_data: Optional[SetupConfiguration] = None) -> SetupConfiguration:
        """Run setup wizard to configure working environment."""
        return self.setup_wizard.run_automated_setup(setup_data)

    def discover_environment(self) -> CompleteDiscoveryAudit:
        """Run full auto-discovery audit."""
        return self.auto_discovery.run_full_discovery()

    def create_project(
        self,
        idea: str,
        project_name: Optional[str] = None,
        workspace_dir: Optional[str | Path] = None,
    ) -> FlowExecutionRecord:
        """Create and execute a project end-to-end from a single user prompt."""
        return self.project_flow.execute_project_from_prompt(
            idea=idea,
            project_name=project_name,
            workspace_dir=workspace_dir,
        )
