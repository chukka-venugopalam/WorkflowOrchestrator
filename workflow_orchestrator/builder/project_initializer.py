"""Project Initializer — creates a new project, initializes workspace, creates contract, registers session, creates project state.

Coordinates with:
- WorkspaceManager for workspace provisioning
- ContractManager for contract creation
- SessionRuntime for session registration
- ProjectMemory for state persistence
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    BuilderConfig,
    PhaseState,
    ProjectState,
)
from workflow_orchestrator.core.event_bus import Event, EventBus
from workflow_orchestrator.core.workspace_manager import WorkspaceManager

logger = logging.getLogger(__name__)


class ProjectInitializer:
    """Creates and initializes new builder projects.

    Full initialization flow:
    1. Generate project ID and structure
    2. Initialize workspace directory
    3. Create project contract
    4. Register session
    5. Create initial project state
    6. Persist to project memory
    7. Publish events

    Usage:
        >>> initializer = ProjectInitializer(event_bus=bus, workspace_mgr=wm)
        >>> state = initializer.initialize("Food Delivery Platform")
    """

    def __init__(
        self,
        config: BuilderConfig | None = None,
        event_bus: EventBus | None = None,
        workspace_manager: WorkspaceManager | None = None,
    ) -> None:
        """Initialize the Project Initializer.

        Args:
            config: Builder configuration. Uses defaults if not provided.
            event_bus: Optional EventBus for publishing events.
            workspace_manager: Optional WorkspaceManager for workspace creation.
        """
        self._config = config or BuilderConfig()
        self._event_bus = event_bus
        self._workspace_manager = workspace_manager

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(
        self,
        project_name: str,
        description: str = "",
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProjectState:
        """Initialize a new project.

        Args:
            project_name: Human-readable project name.
            description: Optional project description.
            project_id: Optional explicit project ID. Auto-generated if not provided.
            metadata: Additional project metadata.

        Returns:
            The created ProjectState.
        """
        pid = project_id or uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()

        # Create initial project state
        state = ProjectState(
            project_id=pid,
            project_name=project_name,
            status="initializing",
            current_phase="classifying",
            started_at=now,
            updated_at=now,
            metadata={
                "description": description,
                "created_at": now,
                **(metadata or {}),
            },
        )

        # Create initial phase states
        for phase_name in [
            "classifying", "requirements", "architecture", "planning",
            "task_creation", "workflow_generation", "provider_assignment",
            "execution_planning", "executing", "verifying", "documenting", "deploying",
        ]:
            state.phases[phase_name] = PhaseState(phase=phase_name, status="pending")

        # Mark classifying as current
        state.phases["classifying"].status = "running"
        state.phases["classifying"].started_at = now

        # Initialize workspace directory
        self._create_project_directory(pid, project_name)

        # Persist state
        self._save_project_state(state, pid)

        # Publish events
        self._publish_event("builder.initialized", {
            "project_id": pid,
            "project_name": project_name,
            "status": state.status,
        })

        logger.info(
            "Initialized project '%s' (ID: %s) with %d phases",
            project_name, pid, len(state.phases),
        )
        return state

    # ------------------------------------------------------------------
    # Workspace management
    # ------------------------------------------------------------------

    def _create_project_directory(self, project_id: str, project_name: str) -> Path:
        """Create the project directory structure.

        Args:
            project_id: The project identifier.
            project_name: The project name for directory naming.

        Returns:
            Path to the project root.
        """
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name)
        safe_name = safe_name.strip().replace(" ", "_").lower()

        project_root = Path(self._config.project_root)
        if not project_root.is_absolute():
            project_root = Path.cwd() / project_root

        project_dir = project_root / safe_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (project_dir / self._config.state_dir).mkdir(exist_ok=True)
        (project_dir / self._config.workflows_dir).mkdir(exist_ok=True)
        (project_dir / self._config.artifacts_dir).mkdir(exist_ok=True)
        (project_dir / self._config.docs_dir).mkdir(exist_ok=True)

        logger.debug("Created project directory at %s", project_dir)
        return project_dir

    # ------------------------------------------------------------------
    # Contract creation
    # ------------------------------------------------------------------

    def create_contract(
        self,
        project_id: str,
        project_name: str,
        vision: str,
        requirements: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an initial project contract.

        Args:
            project_id: The project identifier.
            project_name: The project name.
            vision: Project vision statement.
            requirements: Optional initial requirements list.

        Returns:
            The contract data as a dictionary.
        """
        contract = {
            "contract_id": uuid.uuid4().hex[:12],
            "project_id": project_id,
            "project_name": project_name,
            "version": "1.0.0",
            "status": "draft",
            "vision": vision,
            "requirements": requirements or [],
            "architecture": "",
            "folder_structure": "",
            "coding_standards": "",
            "tech_stack": {
                "framework": "",
                "language": "",
                "styling": "",
                "deployment": "",
                "database": "",
                "testing": "",
                "ci_cd": "",
                "additional": [],
            },
            "constraints": [],
            "milestones": [],
            "acceptance_criteria": [],
            "human_decisions": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Persist contract
        project_dir = self._resolve_project_dir(project_id, project_name)
        state_dir = project_dir / self._config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "contract.json").write_text(json.dumps(contract, indent=2), encoding="utf-8")

        self._publish_event("builder.contract_created", {
            "project_id": project_id,
            "contract_id": contract["contract_id"],
            "version": contract["version"],
        })

        logger.info("Created contract for project '%s'", project_id)
        return contract

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _save_project_state(self, state: ProjectState, project_name: str) -> None:
        """Save project state to disk.

        Args:
            state: The project state to save.
            project_name: The project name for directory resolution.
        """
        project_dir = self._resolve_project_dir(state.project_id, project_name)
        state_dir = project_dir / self._config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)

        state_file = state_dir / "project_state.json"
        state_file.write_text(json.dumps(self._state_to_dict(state), indent=2), encoding="utf-8")

    def _state_to_dict(self, state: ProjectState) -> dict[str, Any]:
        """Serialize project state to dictionary.

        Args:
            state: The project state.

        Returns:
            JSON-compatible dictionary.
        """
        return {
            "project_id": state.project_id,
            "project_name": state.project_name,
            "project_type": state.project_type,
            "status": state.status,
            "current_phase": state.current_phase,
            "phases": {
                name: {
                    "phase": ps.phase,
                    "status": ps.status,
                    "started_at": ps.started_at,
                    "completed_at": ps.completed_at,
                    "completed_tasks": ps.completed_tasks,
                    "failed_tasks": ps.failed_tasks,
                    "artifacts": ps.artifacts,
                    "metadata": ps.metadata,
                }
                for name, ps in state.phases.items()
            },
            "completed_phases": state.completed_phases,
            "failed_phases": state.failed_phases,
            "started_at": state.started_at,
            "updated_at": state.updated_at,
            "completed_at": state.completed_at,
            "metadata": state.metadata,
        }

    def _resolve_project_dir(self, project_id: str, project_name: str) -> Path:
        """Resolve the project directory path.

        Args:
            project_id: The project identifier.
            project_name: The project name.

        Returns:
            Path to the project root directory.
        """
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in project_name)
        safe_name = safe_name.strip().replace(" ", "_").lower()

        project_root = Path(self._config.project_root)
        if not project_root.is_absolute():
            project_root = Path.cwd() / project_root

        return project_root / safe_name

    # ------------------------------------------------------------------
    # Session registration
    # ------------------------------------------------------------------

    def register_session(
        self,
        project_id: str,
        project_name: str,
        session_id: str | None = None,
    ) -> str:
        """Register a builder session (non-intrusive, returns session ID).

        Args:
            project_id: The project identifier.
            project_name: The project name.
            session_id: Optional explicit session ID.

        Returns:
            The session ID.
        """
        sid = session_id or uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()

        project_dir = self._resolve_project_dir(project_id, project_name)
        state_dir = project_dir / self._config.state_dir
        state_dir.mkdir(parents=True, exist_ok=True)

        session_data = {
            "session_id": sid,
            "project_id": project_id,
            "project_name": project_name,
            "created_at": now,
            "updated_at": now,
            "status": "active",
        }
        (state_dir / "builder_session.json").write_text(
            json.dumps(session_data, indent=2), encoding="utf-8",
        )

        logger.debug("Registered session '%s' for project '%s'", sid, project_id)
        return sid

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a builder event if an event bus is available.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="project_initializer",
            ))
        except Exception:
            logger.debug("Failed to publish event '%s'", event_type, exc_info=True)
