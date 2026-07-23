"""Tests for ProjectInitializer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from workflow_orchestrator.builder.project_initializer import ProjectInitializer
from workflow_orchestrator.builder.data_models import BuilderConfig


class TestProjectInitializer:
    """Tests for ProjectInitializer."""

    def setup_method(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.config = BuilderConfig(project_root=self.temp_dir)
        self.initializer = ProjectInitializer(config=self.config)

    def test_initialize_creates_project_state(self) -> None:
        state = self.initializer.initialize("Test Project", "A test project")
        assert state.project_id != ""
        assert state.project_name == "Test Project"
        assert state.status == "initializing"
        assert state.current_phase == "classifying"

    def test_initialize_with_custom_id(self) -> None:
        state = self.initializer.initialize("Test", project_id="custom_id_123")
        assert state.project_id == "custom_id_123"

    def test_initialize_creates_phases(self) -> None:
        state = self.initializer.initialize("Test")
        assert len(state.phases) > 0
        assert "classifying" in state.phases
        assert "executing" in state.phases
        assert state.phases["classifying"].status == "running"

    def test_initialize_timestamp(self) -> None:
        state = self.initializer.initialize("Test")
        assert state.started_at != ""
        assert state.updated_at != ""

    def test_create_contract(self) -> None:
        contract = self.initializer.create_contract(
            "p1", "Test Project", "Build a test platform",
        )
        assert contract["project_id"] == "p1"
        assert contract["version"] == "1.0.0"
        assert contract["status"] == "draft"
        assert "contract_id" in contract

    def test_create_contract_with_requirements(self) -> None:
        contract = self.initializer.create_contract(
            "p1", "Test", "Vision", ["req1", "req2"],
        )
        assert len(contract["requirements"]) == 2

    def test_register_session(self) -> None:
        sid = self.initializer.register_session("p1", "Test Project")
        assert sid != ""
        assert len(sid) > 0

    def test_register_session_custom_id(self) -> None:
        sid = self.initializer.register_session("p1", "Test", session_id="my_session")
        assert sid == "my_session"

    def test_metadata_stored(self) -> None:
        state = self.initializer.initialize("Test", metadata={"source": "cli"})
        assert state.metadata.get("source") == "cli"

    def test_project_directory_created(self) -> None:
        state = self.initializer.initialize("My Project Name")
        project_dir = Path(self.temp_dir) / "my_project_name"
        assert project_dir.exists()
        assert (project_dir / ".builder").exists()

    def test_empty_project_name(self) -> None:
        state = self.initializer.initialize("")
        assert state.project_id != ""

    def test_event_bus_none(self) -> None:
        initializer = ProjectInitializer(config=self.config)
        state = initializer.initialize("Test")
        assert state.project_name == "Test"
