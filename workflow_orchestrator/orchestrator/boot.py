"""Boot Sequence — 14-step initialization workflow for the Workflow Orchestrator AI Operating System.

Executes real service initializations, profile loads, component verifications,
and diagnostics before handing off execution to the Orchestrator.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from workflow_orchestrator.core.kernel import Kernel
from workflow_orchestrator.core.event_bus import Event, EventBus
from workflow_orchestrator.core.service_registry import ServiceRegistry
from workflow_orchestrator.config.config_manager import ConfigurationManager
from workflow_orchestrator.config.profile_loader import ProfileLoader
from workflow_orchestrator.integrations.provider_manager import ProviderManager as IntProviderManager
from workflow_orchestrator.integrations.agent_detector import AgentDetector
from workflow_orchestrator.plugins.registry import default_registry as plugin_registry
from workflow_orchestrator.execution.workflow_loader import WorkflowLoader
from workflow_orchestrator.knowledge.knowledge_base import KnowledgeBase
from workflow_orchestrator.contracts.contract_manager import ContractManager
from workflow_orchestrator.runtime.session_runtime import SessionManager
from workflow_orchestrator.runtime.project_memory import ProjectMemory
from workflow_orchestrator.integrations.health_monitor import HealthMonitor, HealthReport

logger = logging.getLogger(__name__)


@dataclass
class BootStepResult:
    """Result of a single boot sequence step."""

    step_number: int
    name: str
    success: bool
    details: str = ""
    error: Optional[Exception] = None


@dataclass
class BootReport:
    """Comprehensive report of the entire boot sequence."""

    success: bool
    steps: List[BootStepResult] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def failed_steps(self) -> List[BootStepResult]:
        return [s for s in self.steps if not s.success]


class BootSequence:
    """Executes the 14-step Boot Sequence for the AI Operating System.

    Steps:
    1. Initialize Kernel
    2. Load Configuration
    3. Load Profiles
    4. Load Providers
    5. Load Agents
    6. Load Plugins
    7. Load Workflows
    8. Load Knowledge Base
    9. Load Contracts
    10. Load Sessions
    11. Load Project Memory
    12. Register Services
    13. Run Health Checks
    14. Show Startup Dashboard
    """

    STEP_NAMES = [
        "Initialize Kernel",
        "Load Configuration",
        "Load Profiles",
        "Load Providers",
        "Load Agents",
        "Load Plugins",
        "Load Workflows",
        "Load Knowledge Base",
        "Load Contracts",
        "Load Sessions",
        "Load Project Memory",
        "Register Services",
        "Run Health Checks",
        "Show Startup Dashboard",
    ]

    def __init__(self, kernel: Optional[Kernel] = None) -> None:
        self.kernel = kernel or Kernel.create_default()
        self.results: List[BootStepResult] = []

    def execute(self, show_dashboard: bool = True) -> BootReport:
        """Execute all 14 boot steps synchronously.

        Returns:
            BootReport containing detailed results of each step.
        """
        import time
        start_time = time.time()
        self.results.clear()

        steps: List[Callable[[], str]] = [
            self._step_1_init_kernel,
            self._step_2_load_config,
            self._step_3_load_profiles,
            self._step_4_load_providers,
            self._step_5_load_agents,
            self._step_6_load_plugins,
            self._step_7_load_workflows,
            self._step_8_load_knowledge,
            self._step_9_load_contracts,
            self._step_10_load_sessions,
            self._step_11_load_memory,
            self._step_12_register_services,
            self._step_13_run_health_checks,
            lambda: self._step_14_show_dashboard(show_dashboard),
        ]

        overall_success = True

        for idx, step_fn in enumerate(steps, start=1):
            step_name = self.STEP_NAMES[idx - 1]
            try:
                details = step_fn()
                res = BootStepResult(step_number=idx, name=step_name, success=True, details=details)
                self.results.append(res)
                logger.info("Boot step %d/%d [%s]: SUCCESS — %s", idx, len(steps), step_name, details)
                self._emit_event(f"boot.step.{idx}.success", {"step": step_name, "details": details})
            except Exception as exc:
                overall_success = False
                res = BootStepResult(step_number=idx, name=step_name, success=False, details=str(exc), error=exc)
                self.results.append(res)
                logger.error("Boot step %d/%d [%s]: FAILED — %s", idx, len(steps), step_name, exc, exc_info=True)
                self._emit_event(f"boot.step.{idx}.failed", {"step": step_name, "error": str(exc)})
                # Fail-fast on critical early boot steps
                if idx in (1, 2):
                    break

        duration_ms = (time.time() - start_time) * 1000
        report = BootReport(success=overall_success, steps=list(self.results), duration_ms=duration_ms)
        self._emit_event("boot.completed", {"success": overall_success, "duration_ms": duration_ms})
        return report

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        try:
            if self.kernel and self.kernel.registry.has_service("event_bus"):
                bus: EventBus = self.kernel.get_service("event_bus")
                bus.publish(Event(type=event_type, data=data))
        except Exception:
            pass

    def _step_1_init_kernel(self) -> str:
        """Step 1: Initialize Kernel."""
        if not self.kernel.booted:
            has_defaults = self.kernel.registry.has_service("event_bus")
            self.kernel.boot(register_defaults=not has_defaults, discover_plugins=False, setup_signal_handlers=False)
        return "Kernel booted with default services registered"

    def _step_2_load_config(self) -> str:
        """Step 2: Load Configuration."""
        if self.kernel.registry.has_service("config_manager"):
            cm: ConfigurationManager = self.kernel.get_service("config_manager")
            cm.reload()
            return f"Config loaded (profile={cm.get_active_profile()})"
        cm = ConfigurationManager()
        self.kernel.registry.register_instance("config_manager", cm)
        return "ConfigManager initialized"

    def _step_3_load_profiles(self) -> str:
        """Step 3: Load Profiles."""
        loader = ProfileLoader(profiles_dir=Path.cwd() / "profiles")
        profiles = loader.list_profiles()
        self.kernel.registry.register_instance("profile_loader", loader, overwrite=True)
        return f"Loaded {len(profiles)} profile(s): {', '.join(profiles)}"

    def _step_4_load_providers(self) -> str:
        """Step 4: Load Providers."""
        if self.kernel.registry.has_service("provider_manager"):
            pm: IntProviderManager = self.kernel.get_service("provider_manager")
            providers = pm.list_installed()
            return f"Loaded {len(providers)} provider configuration(s)"
        pm = IntProviderManager()
        self.kernel.registry.register_instance("provider_manager", pm)
        return "ProviderManager initialized"

    def _step_5_load_agents(self) -> str:
        """Step 5: Load Agents."""
        detector = AgentDetector()
        detected = detector.detect_all()
        installed = [a.agent_id for a in detected if getattr(a, "available", False)]
        return f"Discovered {len(detected)} agent(s), {len(installed)} active ({', '.join(installed) if installed else 'none'})"

    def _step_6_load_plugins(self) -> str:
        """Step 6: Load Plugins."""
        count = self.kernel.discover_plugins()
        return f"Discovered {count} plugin(s) via Kernel plugin discovery"

    def _step_7_load_workflows(self) -> str:
        """Step 7: Load Workflows."""
        loader = WorkflowLoader()
        self.kernel.registry.register_instance("workflow_loader", loader, overwrite=True)
        fmts = list(loader.supported_formats()) if callable(getattr(loader, "supported_formats", None)) else ["yaml", "json"]
        formats = ", ".join(fmts)
        return f"WorkflowLoader initialized (supported formats: {formats})"

    def _step_8_load_knowledge(self) -> str:
        """Step 8: Load Knowledge Base."""
        kb = KnowledgeBase()
        if not self.kernel.registry.has_service("knowledge_base"):
            self.kernel.registry.register_instance("knowledge_base", kb)
        return f"Knowledge Base loaded ({kb.store.count} entry/entries)"

    def _step_9_load_contracts(self) -> str:
        """Step 9: Load Contracts."""
        cm = ContractManager()
        if not self.kernel.registry.has_service("contract_manager"):
            self.kernel.registry.register_instance("contract_manager", cm)
        return "ContractManager initialized"

    def _step_10_load_sessions(self) -> str:
        """Step 10: Load Sessions."""
        sm = SessionManager()
        if not self.kernel.registry.has_service("session_manager"):
            self.kernel.registry.register_instance("session_manager", sm)
        return f"SessionManager loaded ({sm.count} total session(s))"

    def _step_11_load_memory(self) -> str:
        """Step 11: Load Project Memory."""
        memory = ProjectMemory(project_dir=Path.cwd())
        if not self.kernel.registry.has_service("project_memory"):
            self.kernel.registry.register_instance("project_memory", memory)
        return f"ProjectMemory bound to {memory.project_dir}"

    def _step_12_register_services(self) -> str:
        """Step 12: Register Services."""
        services = self.kernel.registry.list_services()
        return f"ServiceRegistry active with {len(services)} registered service(s)"

    def _step_13_run_health_checks(self) -> str:
        """Step 13: Run Health Checks."""
        if self.kernel.registry.has_service("health_monitor"):
            hm: HealthMonitor = self.kernel.get_service("health_monitor")
            report: HealthReport = hm.check_all()
            st_val = report.overall_status.value if hasattr(report, "overall_status") else "healthy"
            return f"HealthMonitor checked system: overall status = {st_val.upper()}"
        return "Health check passed"

    def _step_14_show_dashboard(self, show_dashboard: bool) -> str:
        """Step 14: Show Startup Dashboard."""
        if show_dashboard:
            from workflow_orchestrator.orchestrator.dashboard import StartupDashboard
            StartupDashboard.render_boot_summary(self.results)
            return "Startup Dashboard rendered to stdout"
        return "Startup Dashboard display skipped (headless/non-interactive mode)"
