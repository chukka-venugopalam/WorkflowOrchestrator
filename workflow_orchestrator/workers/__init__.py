"""Desktop Workers Package — Local Desktop AI Operating System Workers.

Exposes DesktopWorker abstraction layer and worker registry.
"""

from __future__ import annotations

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    WorkerState,
    SkillCapability,
    DesktopWorkerTaskResult,
)
from workflow_orchestrator.workers.worker_registry import DesktopWorkerRegistry

__all__ = [
    "DesktopWorker",
    "WorkerState",
    "SkillCapability",
    "DesktopWorkerTaskResult",
    "DesktopWorkerRegistry",
]
