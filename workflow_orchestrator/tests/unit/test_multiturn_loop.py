"""Unit tests for Multi-Turn Agent Conversation Loop in DesktopWorker."""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict

from workflow_orchestrator.workers.desktop_worker import (
    DesktopWorker,
    DesktopWorkerTaskResult,
    WorkerState,
)


class MockMultiTurnWorker(DesktopWorker):
    """Mock worker to test multi-turn conversation loop mechanics."""

    def __init__(self, behavior: str = "fast_path") -> None:
        super().__init__(
            worker_id="mock_multiturn",
            name="Mock MultiTurn Worker",
            skills=["general_coding"],
            transport_type="terminal",
        )
        self.behavior = behavior
        self.turn_count = 0

    def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
        self.turn_count += 1
        turn = task_payload.get("turn", 1)
        workspace_dir = Path(task_payload.get("workspace_dir", Path.cwd()))

        if self.behavior == "fast_path":
            # Turn 1 completes immediately with file change and marker
            out_file = workspace_dir / f"turn_{turn}.txt"
            out_file.write_text(f"Turn {turn} content", encoding="utf-8")
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"Turn {turn} complete. TASK COMPLETE.",
                generated_files=[out_file],
            )

        elif self.behavior == "turn_3_completion":
            out_file = workspace_dir / f"turn_{turn}.txt"
            out_file.write_text(f"Turn {turn} content", encoding="utf-8")

            if turn < 3:
                return DesktopWorkerTaskResult(
                    success=True,
                    output_text=f"Working on step {turn}...",
                    generated_files=[out_file],
                )
            else:
                return DesktopWorkerTaskResult(
                    success=True,
                    output_text=f"Step 3 finished. TASK COMPLETE.",
                    generated_files=[out_file],
                )

        elif self.behavior == "max_turns_exceeded":
            out_file = workspace_dir / f"turn_{turn}.txt"
            out_file.write_text(f"Turn {turn} work", encoding="utf-8")
            return DesktopWorkerTaskResult(
                success=True,
                output_text=f"Still working on step {turn}...",
                generated_files=[out_file],
            )

        elif self.behavior == "marker_without_files":
            # Emits completion marker text but NO files are created or modified
            return DesktopWorkerTaskResult(
                success=True,
                output_text="I am totally done! TASK COMPLETE.",
                generated_files=[],
            )

        return DesktopWorkerTaskResult(success=False, error_message="Unknown behavior")


class TestMultiTurnConversationLoop:
    """Targeted unit tests for Task 5 requirements."""

    def test_turn_1_completion_fast_path(self, tmp_path: Path) -> None:
        worker = MockMultiTurnWorker(behavior="fast_path")
        worker.start()

        res = worker.execute({"task_id": "test_1", "workspace_dir": str(tmp_path), "max_turns": 8})

        assert res.success is True
        assert worker.turn_count == 1
        assert res.metadata.get("turns_taken") == 1
        assert res.metadata.get("completion_detected") is True

    def test_turn_3_completion(self, tmp_path: Path) -> None:
        worker = MockMultiTurnWorker(behavior="turn_3_completion")
        worker.start()

        res = worker.execute({"task_id": "test_3", "workspace_dir": str(tmp_path), "max_turns": 8})

        assert res.success is True
        assert worker.turn_count == 3
        assert res.metadata.get("turns_taken") == 3
        assert res.metadata.get("completion_detected") is True

    def test_max_turns_exceeded_fails(self, tmp_path: Path) -> None:
        worker = MockMultiTurnWorker(behavior="max_turns_exceeded")
        worker.start()

        res = worker.execute({"task_id": "test_max", "workspace_dir": str(tmp_path), "max_turns": 4})

        assert res.success is False
        assert worker.turn_count == 4
        assert "did not reach completion within 4 turns" in (res.error_message or "")
        assert res.metadata.get("completion_detected") is False

    def test_marker_without_files_rejected(self, tmp_path: Path) -> None:
        worker = MockMultiTurnWorker(behavior="marker_without_files")
        worker.start()

        # Marker present but no files created/modified -> should NOT detect completion and hit max_turns failure
        res = worker.execute({"task_id": "test_lying_agent", "workspace_dir": str(tmp_path), "max_turns": 3})

        assert res.success is False
        assert worker.turn_count == 3
        assert "did not reach completion within 3 turns" in (res.error_message or "")
        assert res.metadata.get("completion_detected") is False

    def test_substring_incomplete_not_matched(self, tmp_path: Path) -> None:
        class IncompleteWordWorker(DesktopWorker):
            def discover(self) -> bool:
                return True

            def _execute_desktop_task(self, task_payload: Dict[str, Any]) -> DesktopWorkerTaskResult:
                workspace_dir = Path(task_payload.get("workspace_dir", Path.cwd()))
                (workspace_dir / "file.txt").write_text("mod")
                return DesktopWorkerTaskResult(
                    success=True,
                    output_text="The task remains incomplete, still working on tests.",
                )

        worker = IncompleteWordWorker(worker_id="inc_worker", name="Incomplete Worker")
        res = worker.execute({"task_id": "inc_task", "workspace_dir": str(tmp_path), "max_turns": 2})

        assert res.success is False
        assert "did not reach completion within 2 turns" in (res.error_message or "")
        assert res.metadata.get("completion_detected") is False
