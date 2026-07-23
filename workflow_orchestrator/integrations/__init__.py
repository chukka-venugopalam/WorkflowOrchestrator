"""Integrations package — automatic discovery, configuration, and lifecycle management.

This package contains all integration modules that handle automatic
discovery of installed tools, providers, agents, browsers, desktop apps,
CLI tools, MCP servers, and runtime environments. It also manages
provider/agent lifecycle, credential storage, health monitoring, and updates.

Packages:
    provider_manager: Owns provider lifecycle (install, remove, enable, disable, configure, validate, repair, update)
    provider_detector: Automatically detects installed providers
    provider_installer: Guides user through installation if missing
    provider_configuration: Creates and manages provider YAML configuration
    credential_manager: Stores credentials securely
    transport_factory: Creates transports dynamically based on configuration
    browser_manager: Detects installed browsers and profiles
    desktop_manager: Detects desktop applications
    cli_manager: Detects CLI tools and runtimes
    mcp_manager: Discovers MCP servers and registers capabilities
    api_manager: Manages REST API providers
    agent_detector: Discovers installed coding agents
    workspace_detector: Detects current workspace type and project structure
    environment_detector: Detects runtime environment (OS, hardware, languages)
    tool_detector: Detects installed developer tools
    dependency_detector: Detects project dependencies and frameworks
    version_manager: Tracks versions and compatibility
    health_monitor: Continuous monitoring of all components
    update_manager: Checks for updates
"""

from __future__ import annotations

from workflow_orchestrator.integrations.provider_manager import ProviderManager, ProviderStatus as IntegrationProviderStatus
from workflow_orchestrator.integrations.provider_detector import ProviderDetector
from workflow_orchestrator.integrations.provider_installer import ProviderInstaller
from workflow_orchestrator.integrations.provider_configuration import ProviderConfiguration
from workflow_orchestrator.integrations.credential_manager import CredentialManager
from workflow_orchestrator.integrations.transport_factory import TransportFactory
from workflow_orchestrator.integrations.browser_manager import BrowserManager
from workflow_orchestrator.integrations.desktop_manager import DesktopManager
from workflow_orchestrator.integrations.cli_manager import CliManager
from workflow_orchestrator.integrations.mcp_manager import McpManager
from workflow_orchestrator.integrations.api_manager import ApiManager
from workflow_orchestrator.integrations.agent_detector import AgentDetector
from workflow_orchestrator.integrations.workspace_detector import WorkspaceDetector
from workflow_orchestrator.integrations.environment_detector import EnvironmentDetector
from workflow_orchestrator.integrations.tool_detector import ToolDetector
from workflow_orchestrator.integrations.dependency_detector import DependencyDetector
from workflow_orchestrator.integrations.version_manager import VersionManager
from workflow_orchestrator.integrations.health_monitor import HealthMonitor
from workflow_orchestrator.integrations.update_manager import UpdateManager

__all__ = [
    "ProviderManager",
    "IntegrationProviderStatus",
    "ProviderDetector",
    "ProviderInstaller",
    "ProviderConfiguration",
    "CredentialManager",
    "TransportFactory",
    "BrowserManager",
    "DesktopManager",
    "CliManager",
    "McpManager",
    "ApiManager",
    "AgentDetector",
    "WorkspaceDetector",
    "EnvironmentDetector",
    "ToolDetector",
    "DependencyDetector",
    "VersionManager",
    "HealthMonitor",
    "UpdateManager",
]
