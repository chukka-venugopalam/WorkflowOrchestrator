"""Core orchestration layer — Layer 1 of the Workflow Orchestrator.

This package contains the deterministic core of the system:
- Kernel: Application entry point, startup/shutdown orchestration
- Service Registry: Dependency injection container
- Lifecycle: Startup/shutdown lifecycle hooks
- Event Bus: In-process publish/subscribe
- State Engine: State machine with append-only transition log
- Capability Registry: Capability indexing and resolution
- Workspace Manager: Sandboxed workspace provisioning
- Artifact Manager: Content-addressed artifact storage
- Logger: Unified logging with correlation IDs and execution IDs
"""

from __future__ import annotations

__all__ = [
    # Kernel
    "Kernel",
    "ServiceRegistry",
    "LifecycleManager",
    "BootstrapSequence",
    "ShutdownHandler",
    # Event Bus
    "EventBus",
    "Subscription",
    "Event",
    # State Engine
    "StateEngine",
    "StateStore",
    "FileSystemStateStore",
    "TransitionRecord",
    "RunSnapshot",
    "HeartbeatRecord",
    # Capability Registry
    "CapabilityRegistry",
    "CapabilityManifest",
    "CapabilityTaxonomy",
    "RankedCandidates",
    "CapabilityRequirement",
    # Workspace Manager
    "WorkspaceManager",
    "WorkspaceHandle",
    "WorkspaceScope",
    # Artifact Manager
    "ArtifactManager",
    "ArtifactRef",
    "ArtifactMetadata",
    # Logger
    "UnifiedLogger",
    "get_logger",
    "configure_logging",
]

# Kernel
from workflow_orchestrator.core.kernel import Kernel
from workflow_orchestrator.core.service_registry import ServiceRegistry
from workflow_orchestrator.core.lifecycle import LifecycleManager
from workflow_orchestrator.core.bootstrap import BootstrapSequence
from workflow_orchestrator.core.shutdown import ShutdownHandler

# Event Bus
from workflow_orchestrator.core.event_bus import EventBus, Subscription, Event

# State Engine
from workflow_orchestrator.core.state_engine import (
    StateEngine,
    StateStore,
    FileSystemStateStore,
    TransitionRecord,
    RunSnapshot,
    HeartbeatRecord,
)

# Capability Registry
from workflow_orchestrator.core.capability_registry import (
    CapabilityRegistry,
    CapabilityManifest,
    CapabilityTaxonomy,
    RankedCandidates,
    CapabilityRequirement,
)

# Workspace Manager
from workflow_orchestrator.core.workspace_manager import (
    WorkspaceManager,
    WorkspaceHandle,
    WorkspaceScope,
)

# Artifact Manager
from workflow_orchestrator.core.artifact_manager import (
    ArtifactManager,
    ArtifactRef,
    ArtifactMetadata,
)

# Logger
from workflow_orchestrator.core.logger import (
    UnifiedLogger,
    get_logger,
    configure_logging,
)
