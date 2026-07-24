"""Workflow Orchestrator Package — Master Orchestration Layer.

Exposes unified facade classes and engines for the AI Operating System.
"""

from __future__ import annotations

from workflow_orchestrator.orchestrator.orchestrator import Orchestrator
from workflow_orchestrator.orchestrator.boot import BootSequence, BootReport
from workflow_orchestrator.orchestrator.provider_manager import ProviderManager
from workflow_orchestrator.orchestrator.transport_manager import TransportManager
from workflow_orchestrator.orchestrator.agent_manager import AgentManager
from workflow_orchestrator.orchestrator.mcp_manager import MCPManager
from workflow_orchestrator.orchestrator.discovery import AutoDiscovery
from workflow_orchestrator.orchestrator.doctor import WorkflowDoctor
from workflow_orchestrator.orchestrator.first_run import SetupWizard
from workflow_orchestrator.orchestrator.project_flow import ProjectFlowEngine
from workflow_orchestrator.orchestrator.self_healing import SelfHealingEngine
from workflow_orchestrator.orchestrator.dashboard import StartupDashboard, ProjectDashboard

__all__ = [
    "Orchestrator",
    "BootSequence",
    "BootReport",
    "ProviderManager",
    "TransportManager",
    "AgentManager",
    "MCPManager",
    "AutoDiscovery",
    "WorkflowDoctor",
    "SetupWizard",
    "ProjectFlowEngine",
    "SelfHealingEngine",
    "StartupDashboard",
    "ProjectDashboard",
]
