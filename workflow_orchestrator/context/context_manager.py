"""Per-Worker Context Window Manager — Isolated context scoping engine.

Maintains per-worker context windows, sending only relevant files, schemas, diffs, and history.
Prevents sending the entire codebase to workers every time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkerContextWindow:
    """Isolated context window bound to a specific worker."""

    worker_id: str
    active_files: List[Path] = field(default_factory=list)
    recent_history: List[str] = field(default_factory=list)
    contract_rules: List[str] = field(default_factory=list)
    token_limit: int = 4000


class PerWorkerContextManager:
    """Manages isolated per-worker context windows and scopes relevant project files."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.windows: Dict[str, WorkerContextWindow] = {}

    def get_or_create_window(self, worker_id: str) -> WorkerContextWindow:
        """Get or initialize context window for a worker."""
        if worker_id not in self.windows:
            self.windows[worker_id] = WorkerContextWindow(worker_id=worker_id)
        return self.windows[worker_id]

    def build_scoped_payload(
        self,
        worker_id: str,
        task_id: str,
        raw_prompt: str,
        required_skill: str,
    ) -> Dict[str, Any]:
        """Scope files and history for a specific worker task to minimize context overhead."""
        win = self.get_or_create_window(worker_id)
        relevant_files = self._select_relevant_files(required_skill)
        win.active_files = relevant_files

        # Add recent prompt history
        win.recent_history.append(f"Task '{task_id}': {raw_prompt[:60]}")
        if len(win.recent_history) > 5:
            win.recent_history.pop(0)

        file_summaries = []
        for f in relevant_files:
            file_summaries.append(f"File: {f.name} (Size: {f.stat().st_size if f.exists() else 0} bytes)")

        scoped_prompt = (
            f"[SCOPED WORKER CONTEXT]\n"
            f"Worker ID: {worker_id} | Skill: {required_skill}\n"
            f"Relevant Files ({len(relevant_files)}):\n" + "\n".join(file_summaries) + "\n\n"
            f"TASK PROMPT: {raw_prompt}"
        )

        logger.info(f"Built scoped payload for worker '{worker_id}': {len(relevant_files)} files attached.")
        return {
            "worker_id": worker_id,
            "task_id": task_id,
            "prompt": scoped_prompt,
            "raw_prompt": raw_prompt,
            "scoped_files": [str(f) for f in relevant_files],
        }

    def _select_relevant_files(self, required_skill: str) -> List[Path]:
        """Select only relevant files based on worker skill."""
        relevant = []
        if not self.project_root.exists():
            return relevant

        for p in self.project_root.rglob("*"):
            if p.is_file() and not any(part.startswith((".", "__pycache__", "node_modules", ".venv")) for part in p.parts):
                fname = p.name.lower()
                if required_skill == "backend_api" and ("py" in fname or "sql" in fname or "json" in fname):
                    relevant.append(p)
                elif required_skill == "frontend_ui" and ("ts" in fname or "js" in fname or "css" in fname or "html" in fname):
                    relevant.append(p)
                elif required_skill == "unit_testing" and ("test" in fname or "py" in fname):
                    relevant.append(p)
                elif required_skill == "deployment" and ("docker" in fname or "yaml" in fname or "toml" in fname):
                    relevant.append(p)
                if len(relevant) >= 5:
                    break
        return relevant
