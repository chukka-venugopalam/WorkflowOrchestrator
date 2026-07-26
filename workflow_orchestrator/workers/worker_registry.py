"""DesktopWorkerRegistry — registry for managing local desktop AI workers.

Integrates with existing ServiceRegistry and CapabilityRegistry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from workflow_orchestrator.workers.desktop_worker import DesktopWorker, WorkerState

logger = logging.getLogger(__name__)


class DesktopWorkerRegistry:
    """Registry for discovering, managing, and scheduling local desktop AI workers."""

    def __init__(self) -> None:
        self._workers: Dict[str, DesktopWorker] = {}

    def register_worker(self, worker: DesktopWorker) -> None:
        """Register a desktop worker instance."""
        self._workers[worker.worker_id] = worker
        logger.info(f"Registered DesktopWorker: {worker.worker_id} ({worker.name})")

    def unregister_worker(self, worker_id: str) -> bool:
        """Unregister a desktop worker instance."""
        if worker_id in self._workers:
            worker = self._workers.pop(worker_id)
            worker.stop()
            return True
        return False

    def get_worker(self, worker_id: str) -> Optional[DesktopWorker]:
        """Get a registered worker by ID."""
        return self._workers.get(worker_id)

    def list_workers(self, active_only: bool = False) -> List[DesktopWorker]:
        """List registered desktop workers."""
        if active_only:
            return [w for w in self._workers.values() if w.state in (WorkerState.IDLE, WorkerState.BUSY)]
        return list(self._workers.values())

    def find_workers_by_skill(self, skill_name: str) -> List[DesktopWorker]:
        """Find desktop workers offering a specific skill."""
        matching = []
        for worker in self._workers.values():
            for cap in worker.skills:
                if cap.skill_name.lower() == skill_name.lower():
                    matching.append(worker)
                    break
        return matching

    def discover_and_start_all(self) -> int:
        """Discover and auto-start available desktop workers."""
        started_count = 0
        for worker in self._workers.values():
            if worker.discover():
                if worker.start():
                    started_count += 1
        return started_count

    def stop_all(self) -> None:
        """Stop all registered desktop workers."""
        for worker in self._workers.values():
            worker.stop()
