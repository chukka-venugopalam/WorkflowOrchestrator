"""Boot sequence orchestration for the Workflow Orchestrator.

Manages the ordered registration of default services and
the execution of startup logic.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from workflow_orchestrator.core.kernel import Kernel

logger = logging.getLogger(__name__)


class BootstrapSequence:
    """Orchestrates the boot sequence for the kernel.

    Registers default services in the correct order and sets up
    the initial application state.

    Usage:
        >>> bootstrap = BootstrapSequence(kernel)
        >>> bootstrap.register_default_services()
    """

    def __init__(self, kernel: Kernel) -> None:
        """Initialize the bootstrap sequence.

        Args:
            kernel: The kernel instance to bootstrap.
        """
        self._kernel = kernel
        self._registry = kernel.registry
        self._lifecycle = kernel.lifecycle

    def register_default_services(self) -> None:
        """Register all default framework services."""
        self._register_core_services()
        self._register_config_services()
        self._register_plugin_services()
        self._register_execution_services()
        self._register_intelligence_services()
        self._register_provider_services()
        self._register_agent_services()
        self._register_transport_services()
        self._register_runtime_services()
        self._register_builder_services()
        self._register_integration_services()
        self._register_lifecycle_hooks()

    def _register_core_services(self) -> None:
        """Register core framework services."""
        from workflow_orchestrator.core.event_bus import EventBus
        from workflow_orchestrator.core.state_engine import (
            StateEngine,
            FileSystemStateStore,
        )
        from workflow_orchestrator.core.capability_registry import CapabilityRegistry
        from workflow_orchestrator.core.workspace_manager import WorkspaceManager
        from workflow_orchestrator.core.artifact_manager import ArtifactManager

        # Event Bus
        event_bus = EventBus()
        self._registry.register_instance("event_bus", event_bus, description="In-process event bus")

        # State Engine (lazy — needs config for path)
        self._registry.register_factory(
            "state_engine",
            self._create_state_engine,
            dependencies=["config"],
            description="State engine with append-only transition log",
        )

        # Capability Registry
        capability_registry = CapabilityRegistry()
        self._registry.register_instance(
            "capability_registry",
            capability_registry,
            description="Capability indexing and resolution",
        )

        # Workspace Manager
        self._registry.register_factory(
            "workspace_manager",
            self._create_workspace_manager,
            description="Sandboxed workspace provisioning",
        )

        # Artifact Manager
        self._registry.register_factory(
            "artifact_manager",
            self._create_artifact_manager,
            dependencies=["config"],
            description="Content-addressed artifact storage",
        )

    def _register_config_services(self) -> None:
        """Register configuration services."""
        from workflow_orchestrator.config.config_manager import create_config_manager

        config_mgr = create_config_manager()
        self._registry.register_instance(
            "config",
            config_mgr,
            description="Configuration manager",
        )

        # Also register config_manager as 'config_manager' for backward compat
        self._registry.register_instance(
            "config_manager",
            config_mgr,
            description="Configuration manager (alias)",
        )

    def _register_plugin_services(self) -> None:
        """Register plugin services."""
        from workflow_orchestrator.plugins.registry import PluginRegistry

        plugin_registry = PluginRegistry()
        self._registry.register_instance(
            "plugin_registry",
            plugin_registry,
            description="Plugin discovery and management",
        )

    def _register_execution_services(self) -> None:
        """Register execution engine services."""
        from workflow_orchestrator.execution.step_executor import StepExecutor
        from workflow_orchestrator.execution.execution_engine import ExecutionEngine
        from workflow_orchestrator.execution.execution_queue import ExecutionQueue
        from workflow_orchestrator.execution.workflow_engine import WorkflowEngine

        # Step Executor
        self._registry.register_factory(
            "step_executor",
            self._create_step_executor,
            dependencies=["plugin_registry"],
            description="Single step executor with plugin dispatch",
        )

        # Execution Queue
        queue = ExecutionQueue()
        self._registry.register_instance(
            "execution_queue",
            queue,
            description="Step execution queue (FIFO, priority, delayed)",
        )

        # Execution Engine
        self._registry.register_factory(
            "execution_engine",
            self._create_execution_engine,
            dependencies=["step_executor", "event_bus", "state_engine"],
            description="Step execution with dispatch, events, and state tracking",
        )

        # Workflow Engine
        self._registry.register_factory(
            "workflow_engine",
            self._create_workflow_engine,
            dependencies=["execution_engine", "execution_queue", "event_bus", "state_engine", "artifact_manager"],
            description="Top-level workflow lifecycle orchestrator",
        )

    def _register_intelligence_services(self) -> None:
        """Register intelligence plane services."""
        from workflow_orchestrator.intelligence.session import SessionManager
        from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry
        from workflow_orchestrator.intelligence.agent_registry import AgentRegistry
        from workflow_orchestrator.intelligence.capability_matcher import CapabilityMatcher
        from workflow_orchestrator.intelligence.router import Router
        from workflow_orchestrator.intelligence.planner import Planner
        from workflow_orchestrator.intelligence.prompt_builder import PromptBuilder

        # Session Manager
        session_manager = SessionManager()
        self._registry.register_instance(
            "session_manager",
            session_manager,
            description="Session tracking across providers and agents",
        )

        # Provider Registry
        provider_registry = ProviderRegistry()
        self._registry.register_instance(
            "provider_registry",
            provider_registry,
            description="AI provider adapter registry",
        )

        # Agent Registry
        agent_registry = AgentRegistry()
        self._registry.register_instance(
            "agent_registry",
            agent_registry,
            description="Coding agent adapter registry",
        )

        # Capability Matcher
        capability_matcher = CapabilityMatcher(
            provider_registry=provider_registry,
            agent_registry=agent_registry,
        )
        self._registry.register_instance(
            "capability_matcher",
            capability_matcher,
            description="Provider-agent capability matching",
        )

        # Router
        router = Router(capability_matcher=capability_matcher)
        self._registry.register_instance(
            "router",
            router,
            description="Provider-agent routing decisions",
        )

        # Planner
        planner = Planner(capability_matcher=capability_matcher)
        self._registry.register_instance(
            "planner",
            planner,
            description="Workflow planning from goals",
        )

        # Prompt Builder
        prompt_builder = PromptBuilder()
        self._registry.register_instance(
            "prompt_builder",
            prompt_builder,
            description="Structured prompt assembly",
        )

    def _register_provider_services(self) -> None:
        """Register provider runtime services."""
        from workflow_orchestrator.providers.registry import ProviderRegistryRuntime
        from workflow_orchestrator.providers.implementations import (
            ClaudeProvider,
            ChatGPTProvider,
            GeminiProvider,
        )

        provider_registry = self._registry.get_typed("provider_registry", object)
        event_bus = self._registry.get("event_bus")
        capability_registry = self._registry.get("capability_registry")

        # Register default providers into the ProviderRegistry
        for provider_cls in [ClaudeProvider, ChatGPTProvider, GeminiProvider]:
            try:
                provider = provider_cls()
                # Wire event bus for provider-level events
                if hasattr(provider, "set_event_bus"):
                    provider.set_event_bus(event_bus)
                provider_registry.register(provider)
                logger.debug("Registered provider: %s", provider.provider_id)
            except Exception as exc:
                logger.warning("Failed to register provider %s: %s", provider_cls.__name__, exc)

        # Provider Registry Runtime
        provider_registry_runtime = ProviderRegistryRuntime(
            registry=provider_registry,
            event_bus=event_bus,
            capability_registry=capability_registry,
        )
        self._registry.register_instance(
            "provider_registry_runtime",
            provider_registry_runtime,
            description="Provider lifecycle and health management",
        )

    def _register_agent_services(self) -> None:
        """Register agent runtime services."""
        from workflow_orchestrator.agents.implementations import (
            ClaudeCodeAgent,
            CursorAgent,
            CodexCLIAgent,
            GitHubCopilotAgent,
        )

        agent_registry = self._registry.get("agent_registry")

        # Register default agents into the AgentRegistry
        for agent_cls in [ClaudeCodeAgent, CursorAgent, CodexCLIAgent, GitHubCopilotAgent]:
            try:
                agent = agent_cls()
                # Wire event bus for agent-level events
                if hasattr(agent, "set_event_bus"):
                    agent.set_event_bus(event_bus)
                agent_registry.register(agent)
                logger.debug("Registered agent: %s", agent.agent_id)
            except Exception as exc:
                logger.warning("Failed to register agent %s: %s", agent_cls.__name__, exc)

    def _register_transport_services(self) -> None:
        """Register transport runtime services."""
        from workflow_orchestrator.runtime import TransportRuntime
        from workflow_orchestrator.transports import (
            RestApiTransport,
            CliCommandTransport,
            BrowserAutomationTransport,
            McpClientTransport,
            SshCommandTransport,
        )

        event_bus = self._registry.get("event_bus")

        transport_runtime = TransportRuntime(event_bus=event_bus)

        # Register default transports
        transport_runtime.register("rest_api", RestApiTransport())
        transport_runtime.register("cli", CliCommandTransport())
        transport_runtime.register("browser", BrowserAutomationTransport(headless=True))
        transport_runtime.register("desktop", DesktopAutomationTransport())
        transport_runtime.register("mcp", McpClientTransport())
        transport_runtime.register("ssh", SshCommandTransport())

        self._registry.register_instance(
            "transport_runtime",
            transport_runtime,
            description="Transport lifecycle and communication management",
        )

    def _register_runtime_services(self) -> None:
        """Register all runtime orchestrators."""
        from workflow_orchestrator.runtime import (
            ProviderRuntime,
            AgentRuntime,
            SessionRuntime,
            PromptRuntime,
            ArtifactRuntime,
        )

        event_bus = self._registry.get("event_bus")
        config = self._registry.get("config")

        # Provider Runtime
        provider_registry_runtime = self._registry.get("provider_registry_runtime")
        provider_runtime = ProviderRuntime(
            provider_registry_runtime=provider_registry_runtime,
            event_bus=event_bus,
            artifact_manager=self._registry.get("artifact_manager"),
            session_manager=self._registry.get("session_manager"),
        )
        self._registry.register_instance(
            "provider_runtime",
            provider_runtime,
            description="Provider execution and lifecycle orchestration",
        )

        # Agent Runtime
        agent_registry = self._registry.get("agent_registry")
        agent_runtime = AgentRuntime(
            agent_registry=agent_registry,
            event_bus=event_bus,
            artifact_manager=self._registry.get("artifact_manager"),
            session_manager=self._registry.get("session_manager"),
        )
        self._registry.register_instance(
            "agent_runtime",
            agent_runtime,
            description="Agent execution and lifecycle orchestration",
        )

        # Session Runtime
        session_manager = self._registry.get("session_manager")
        session_runtime = SessionRuntime(
            session_manager=session_manager,
            event_bus=event_bus,
            config=config,
        )
        self._registry.register_instance(
            "session_runtime",
            session_runtime,
            description="Persistent session management with pause/resume",
        )

        # Prompt Runtime
        prompt_runtime = PromptRuntime()
        self._registry.register_instance(
            "prompt_runtime",
            prompt_runtime,
            description="Prompt assembly, rendering, and versioning",
        )

        # Artifact Runtime
        artifact_manager = self._registry.get("artifact_manager")
        artifact_runtime = ArtifactRuntime(
            artifact_manager=artifact_manager,
            event_bus=event_bus,
        )
        self._registry.register_instance(
            "artifact_runtime",
            artifact_runtime,
            description="Provider/agent artifact storage with provenance",
        )

    def _register_lifecycle_hooks(self) -> None:
        """Register startup/shutdown lifecycle hooks."""
        from workflow_orchestrator.core.lifecycle import HookPriority

        # Startup: discover plugins
        self._lifecycle.on_startup(
            "discover_plugins",
            self._discover_plugins,
            priority=HookPriority.HIGH,
            description="Discover and load plugins",
        )

        # Shutdown: stop active workflow runs
        self._lifecycle.on_shutdown(
            "cancel_active_runs",
            self._cancel_active_runs,
            priority=HookPriority.HIGH,
            description="Cancel any active workflow runs",
        )

        # Shutdown: save state
        self._lifecycle.on_shutdown(
            "save_state",
            self._save_state,
            priority=HookPriority.NORMAL,
            description="Persist any in-memory state",
        )

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    def _create_state_engine(self, registry: Any) -> Any:
        """Factory: create the StateEngine."""
        from workflow_orchestrator.core.state_engine import (
            StateEngine,
            FileSystemStateStore,
        )

        config = registry.get("config")
        data_dir = Path(config.get("state_dir", ".orchestrator/state"))

        # Resolve data_dir relative to project root if relative
        if not data_dir.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            data_dir = project_root / "data" / "state"

        store = FileSystemStateStore(data_dir)
        return StateEngine(store=store)

    def _create_workspace_manager(self, registry: Any) -> Any:
        """Factory: create the WorkspaceManager."""
        from workflow_orchestrator.core.workspace_manager import WorkspaceManager
        import tempfile

        base_path = Path(tempfile.gettempdir()) / "workflow_orchestrator" / "workspaces"
        return WorkspaceManager(base_path=base_path)

    def _create_artifact_manager(self, registry: Any) -> Any:
        """Factory: create the ArtifactManager."""
        from workflow_orchestrator.core.artifact_manager import ArtifactManager

        config = registry.get("config")
        artifacts_dir = Path(config.get("artifacts_dir", ".orchestrator/artifacts"))

        if not artifacts_dir.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            artifacts_dir = project_root / "data" / "artifacts"

        return ArtifactManager(base_path=artifacts_dir)

    def _create_step_executor(self, registry: Any) -> Any:
        """Factory: create the StepExecutor."""
        from workflow_orchestrator.execution.step_executor import StepExecutor

        plugin_registry = registry.get("plugin_registry")
        return StepExecutor(plugin_registry=plugin_registry)

    def _create_execution_engine(self, registry: Any) -> Any:
        """Factory: create the ExecutionEngine."""
        from workflow_orchestrator.execution.execution_engine import ExecutionEngine

        step_executor = registry.get("step_executor")
        event_bus = registry.get("event_bus")
        state_engine = registry.get("state_engine")

        return ExecutionEngine(
            executor=step_executor,
            event_bus=event_bus,
            state_engine=state_engine,
        )

    def _create_workflow_engine(self, registry: Any) -> Any:
        """Factory: create the WorkflowEngine."""
        from workflow_orchestrator.execution.workflow_engine import WorkflowEngine

        execution_engine = registry.get("execution_engine")
        event_bus = registry.get("event_bus")
        state_engine = registry.get("state_engine")
        artifact_manager = registry.get("artifact_manager")

        return WorkflowEngine(
            execution_engine=execution_engine,
            event_bus=event_bus,
            state_engine=state_engine,
            artifact_manager=artifact_manager,
        )

    def _register_builder_services(self) -> None:
        """Register Autonomous Project Builder services."""
        from workflow_orchestrator.builder.project_builder import ProjectBuilder, ProjectBuilderConfig
        from workflow_orchestrator.builder.data_models import BuilderConfig

        event_bus = self._registry.get("event_bus")

        builder_config = ProjectBuilderConfig(
            builder=BuilderConfig(),
            auto_execute=False,
            create_checkpoints=True,
            verify_after_tasks=True,
            generate_docs=True,
            generate_deployment=True,
        )

        builder = ProjectBuilder(
            config=builder_config,
            event_bus=event_bus,
            kernel=self._kernel,
        )
        self._registry.register_instance(
            "project_builder",
            builder,
            description="Autonomous Project Builder — transforms ideas into executable projects",
        )

        logger.info("Registered Autonomous Project Builder services")

    def _register_integration_services(self) -> None:
        """Register Integration & Discovery services."""
        from workflow_orchestrator.integrations import (
            ProviderManager,
            ProviderDetector,
            ProviderInstaller,
            ProviderConfiguration,
            CredentialManager,
            TransportFactory,
            BrowserManager,
            DesktopManager,
            CliManager,
            McpManager,
            ApiManager,
            AgentDetector,
            WorkspaceDetector,
            EnvironmentDetector,
            ToolDetector,
            DependencyDetector,
            VersionManager,
            HealthMonitor,
            UpdateManager,
        )

        event_bus = self._registry.get("event_bus")
        config = self._registry.get("config")

        # Provider Manager
        provider_manager = ProviderManager(event_bus=event_bus)
        self._registry.register_instance(
            "provider_manager",
            provider_manager,
            description="Provider lifecycle management (install, remove, enable, disable, configure, validate, repair, update)",
        )

        # Provider Detector
        provider_detector = ProviderDetector()
        self._registry.register_instance(
            "provider_detector",
            provider_detector,
            description="Automatic detection of installed providers",
        )

        # Provider Installer
        provider_installer = ProviderInstaller()
        self._registry.register_instance(
            "provider_installer",
            provider_installer,
            description="Guides installation of missing providers",
        )

        # Provider Configuration
        provider_configuration = ProviderConfiguration(profiles_dir=self._registry.get("config_manager").profiles_dir)
        self._registry.register_instance(
            "provider_configuration",
            provider_configuration,
            description="Provider YAML configuration creation and management",
        )

        # Credential Manager
        credential_manager = CredentialManager(event_bus=event_bus)
        self._registry.register_instance(
            "credential_manager",
            credential_manager,
            description="Secure credential storage with OS keychain support",
        )

        # Transport Factory
        transport_factory = TransportFactory(
            transport_runtime=self._registry.get("transport_runtime"),
            event_bus=event_bus,
        )
        self._registry.register_instance(
            "transport_factory",
            transport_factory,
            description="Dynamic transport creation from configuration",
        )

        # Browser Manager
        browser_manager = BrowserManager()
        self._registry.register_instance(
            "browser_manager",
            browser_manager,
            description="Browser detection and management",
        )

        # Desktop Manager
        desktop_manager = DesktopManager()
        self._registry.register_instance(
            "desktop_manager",
            desktop_manager,
            description="Desktop application detection",
        )

        # CLI Manager
        cli_manager = CliManager()
        self._registry.register_instance(
            "cli_manager",
            cli_manager,
            description="CLI tool detection and version checking",
        )

        # MCP Manager
        mcp_manager = McpManager(event_bus=event_bus)
        self._registry.register_instance(
            "mcp_manager",
            mcp_manager,
            description="MCP server discovery and capability registration",
        )

        # API Manager
        api_manager = ApiManager(event_bus=event_bus)
        self._registry.register_instance(
            "api_manager",
            api_manager,
            description="REST API provider management",
        )

        # Agent Detector
        agent_detector = AgentDetector()
        self._registry.register_instance(
            "agent_detector",
            agent_detector,
            description="Automatic discovery of installed coding agents",
        )

        # Workspace Detector
        workspace_detector = WorkspaceDetector()
        self._registry.register_instance(
            "workspace_detector",
            workspace_detector,
            description="Current workspace type and project detection",
        )

        # Environment Detector
        environment_detector = EnvironmentDetector()
        self._registry.register_instance(
            "environment_detector",
            environment_detector,
            description="Runtime environment detection (OS, hardware, languages)",
        )

        # Tool Detector
        tool_detector = ToolDetector()
        self._registry.register_instance(
            "tool_detector",
            tool_detector,
            description="Installed developer tool detection",
        )

        # Dependency Detector
        dependency_detector = DependencyDetector()
        self._registry.register_instance(
            "dependency_detector",
            dependency_detector,
            description="Project dependency and framework detection",
        )

        # Version Manager
        version_manager = VersionManager(event_bus=event_bus)
        self._registry.register_instance(
            "version_manager",
            version_manager,
            description="Version tracking and compatibility management",
        )

        # Health Monitor
        health_monitor = HealthMonitor(event_bus=event_bus)
        self._registry.register_instance(
            "health_monitor",
            health_monitor,
            description="Continuous health monitoring of all components",
        )

        # Update Manager
        update_manager = UpdateManager(event_bus=event_bus)
        self._registry.register_instance(
            "update_manager",
            update_manager,
            description="Update checking for providers, agents, plugins, and CLI",
        )

        logger.info("Registered %d integration services", 20)

        # Register health checkers automatically
        self._register_health_checkers(health_monitor, provider_detector, cli_manager, environment_detector, tool_detector)

    def _register_health_checkers(
        self,
        health_monitor: HealthMonitor,
        provider_detector: ProviderDetector,
        cli_manager: CliManager,
        environment_detector: EnvironmentDetector,
        tool_detector: ToolDetector,
    ) -> None:
        """Register default health checkers with the health monitor.

        Args:
            health_monitor: The health monitor instance.
            provider_detector: Provider detector for provider health.
            cli_manager: CLI manager for CLI tool health.
            environment_detector: Environment detector for environment health.
            tool_detector: Tool detector for tool health.
        """
        def _check_providers() -> Any:
            from workflow_orchestrator.integrations.health_monitor import HealthCheck as HCheck, HealthStatus as HStatus
            try:
                detected = provider_detector.detect_all()
                if detected:
                    return HCheck(
                        component_id="providers",
                        component_type="provider",
                        status=HStatus.HEALTHY,
                        details={"detected": [p.provider_id for p in detected]},
                    )
                return HCheck(
                    component_id="providers",
                    component_type="provider",
                    status=HStatus.DEGRADED,
                    error="No providers detected",
                )
            except Exception as exc:
                from workflow_orchestrator.integrations.health_monitor import HealthCheck as HCheck, HealthStatus as HStatus
                return HCheck(
                    component_id="providers",
                    component_type="provider",
                    status=HStatus.UNKNOWN,
                    error=str(exc),
                )

        def _check_cli_tools() -> Any:
            from workflow_orchestrator.integrations.health_monitor import HealthCheck as HCheck, HealthStatus as HStatus
            try:
                tools = cli_manager.detect_all()
                available = sum(1 for t in tools if t.available)
                total = len(tools)
                if available == total:
                    status = HStatus.HEALTHY
                elif available > 0:
                    status = HStatus.DEGRADED
                else:
                    status = HStatus.UNHEALTHY
                return HCheck(
                    component_id="cli_tools",
                    component_type="cli",
                    status=status,
                    details={"available": available, "total": total},
                )
            except Exception as exc:
                from workflow_orchestrator.integrations.health_monitor import HealthCheck as HCheck, HealthStatus as HStatus
                return HCheck(
                    component_id="cli_tools",
                    component_type="cli",
                    status=HStatus.UNKNOWN,
                    error=str(exc),
                )

        health_monitor.register_checker("provider", _check_providers)
        health_monitor.register_checker("cli", _check_cli_tools)
        logger.debug("Registered default health checkers")

    # ------------------------------------------------------------------
    # Lifecycle hook handlers
    # ------------------------------------------------------------------

    def _discover_plugins(self) -> bool:
        """Discover and register plugins."""
        from workflow_orchestrator.plugins.registry import PluginRegistry

        if not self._registry.has_service("plugin_registry"):
            logger.warning("Plugin registry not found, skipping plugin discovery")
            return False

        registry = self._registry.get_typed("plugin_registry", PluginRegistry)
        count = registry.discover()
        logger.info("Discovered %d plugins during boot", count)
        return True

    def _cancel_active_runs(self) -> bool:
        """Cancel any active workflow runs during shutdown."""
        if not self._registry.has_service("workflow_engine"):
            return True
        try:
            from workflow_orchestrator.execution.workflow_engine import WorkflowEngine
            engine = self._registry.get_typed("workflow_engine", WorkflowEngine)
            active = engine.list_runs(status="running")
            for run in active:
                engine.cancel_run(run.run_id)
            logger.info("Cancelled %d active workflow runs during shutdown", len(active))
        except Exception:
            logger.debug("Failed to cancel active runs during shutdown", exc_info=True)
        return True

    def _save_state(self) -> bool:
        """Save any in-memory state to disk."""
        # Future: persist state engine checkpoints, etc.
        logger.debug("State save lifecycle hook completed (no-op)")
        return True
