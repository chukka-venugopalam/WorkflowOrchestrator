"""Tests for ResumeManager."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from workflow_orchestrator.builder.resume_manager import ResumeManager
from workflow_orchestrator.builder.data_models import ProjectState


class TestResumeManager:
    """Tests for ResumeManager."""

    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ResumeManager(state_dir=self.temp_dir)

    def test_detect_no_state(self) -> None:
        context = self.manager.detect_resume_context()
        assert not context["can_resume"]
        assert context["reason"] == "No state file found"

    def test_detect_with_state(self) -> None:
        state_file = Path(self.temp_dir) / "project_state.json"
        state_file.write_text(json.dumps({
            "project_id": "p1",
            "project_name": "Test",
            "status": "running",
            "current_phase": "executing",
        }))
        context = self.manager.detect_resume_context()
        assert context["can_resume"]
        assert context["last_phase"] == "executing"

    def test_detect_completed(self) -> None:
        state_file = Path(self.temp_dir) / "project_state.json"
        state_file.write_text(json.dumps({
            "project_id": "p1",
            "status": "completed",
            "current_phase": "completed",
        }))
        context = self.manager.detect_resume_context()
        assert not context["can_resume"]

    def test_resume_returns_state(self) -> None:
        state_file = Path(self.temp_dir) / "project_state.json"
        state_file.write_text(json.dumps({
            "project_id": "p1",
            "project_name": "Test",
            "status": "running",
            "current_phase": "executing",
            "completed_phases": ["planning"],
        }))
        context = self.manager.detect_resume_context()
        state = self.manager.resume(context)
        assert state is not None
        assert state.project_id == "p1"
        assert state.current_phase == "executing"

    def test_resume_no_state(self) -> None:
        state = self.manager.resume({"can_resume": False, "reason": "No state"})
        assert state is None

    def test_crash_flag(self) -> None:
        assert not self.manager.detect_crash()
        self.manager.set_crash_flag()
        assert self.manager.detect_crash()
        self.manager.clear_crash_flag()
        assert not self.manager.detect_crash()

    def test_restore_from_checkpoint_nonexistent(self) -> None:
        state = self.manager.restore_from_checkpoint("nonexistent")
        assert state is None
