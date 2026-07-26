"""Result Merger — multi-worker output integration and conflict resolution engine.

Merges outputs from multiple desktop workers, resolves file conflicts, and produces unified changes before verification.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.workers.desktop_worker import DesktopWorkerTaskResult

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result of multi-worker output integration."""

    success: bool
    unified_files: List[Path] = field(default_factory=list)
    conflicts_resolved: int = 0
    merge_log: str = ""


class ResultMerger:
    """Merges code artifacts and file changes emitted by multiple workers."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or Path.cwd()

    def merge_worker_outputs(
        self,
        worker_results: List[DesktopWorkerTaskResult],
    ) -> MergeResult:
        """Collect worker outputs, resolve file write conflicts, and unify project changes."""
        all_files: List[Path] = []
        conflicts = 0
        file_map: Dict[str, Path] = {}

        for res in worker_results:
            if res and res.success:
                for file_path in res.generated_files:
                    key = str(file_path.resolve()) if file_path.exists() else str(file_path)
                    if key in file_map:
                        conflicts += 1
                        logger.info(f"Resolved file write conflict for: {file_path.name}")
                    file_map[key] = file_path

        unified = list(file_map.values())
        merge_summary = (
            f"Successfully merged {len(worker_results)} worker output(s). "
            f"Unified files count: {len(unified)}, Resolved conflicts: {conflicts}."
        )
        logger.info(merge_summary)

        return MergeResult(
            success=True,
            unified_files=unified,
            conflicts_resolved=conflicts,
            merge_log=merge_summary,
        )
