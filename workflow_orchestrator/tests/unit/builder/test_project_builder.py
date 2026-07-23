"""Tests for ProjectBuilder - the main orchestrator."""

from __future__ import annotations

from workflow_orchestrator.builder.project_builder import ProjectBuilder, ProjectBuilderConfig
from workflow_orchestrator.builder.data_models import BuilderConfig


class TestProjectBuilder:
    """Tests for ProjectBuilder."""

    def setup_method(self) -> None:
        self.builder = ProjectBuilder()

    def test_build_returns_result(self) -> None:
        result = self.builder.build("Build a simple web app")
        assert result is not None
        assert "project_id" in result
        assert "status" in result

    def test_build_project_name(self) -> None:
        result = self.builder.build("Build a food delivery platform", "FoodApp")
        assert result["project_name"] == "FoodApp"

    def test_build_duration(self) -> None:
        result = self.builder.build("Build a test app")
        assert "duration_seconds" in result
        assert result["duration_seconds"] > 0

    def test_build_includes_type(self) -> None:
        result = self.builder.build("Build a web application")
        assert "project_type" in result

    def test_build_includes_progress(self) -> None:
        result = self.builder.build("Build a test")
        assert "progress" in result
        assert "completed_tasks" in result["progress"]

    def test_build_includes_phases(self) -> None:
        result = self.builder.build("Build a test")
        assert "phases" in result
        assert len(result["phases"]) > 0

    def test_build_with_empty_idea(self) -> None:
        result = self.builder.build("")
        assert result["status"] == "completed"

    def test_get_progress_before_build(self) -> None:
        progress = self.builder.get_progress()
        assert progress is not None  # Returns empty snapshot

    def test_get_progress_after_build(self) -> None:
        self.builder.build("Build a test")
        progress = self.builder.get_progress()
        assert progress is not None

    def test_get_summary(self) -> None:
        self.builder.build("Build a test")
        summary = self.builder.get_summary()
        assert "status" in summary

    def test_detect_resume_no_state(self) -> None:
        context = self.builder.detect_resume()
        assert "can_resume" in context

    def test_resume_no_state(self) -> None:
        result = self.builder.resume()
        assert result is None

    def test_check_completion(self) -> None:
        self.builder.build("Build a test")
        status = self.builder.check_completion("project")
        assert status is not None

    def test_list_checkpoints_after_build(self) -> None:
        self.builder.build("Build a test")
        checkpoints = self.builder.list_checkpoints()
        # Checkpoints may or may not be created depending on config
        assert isinstance(checkpoints, list)

    def test_create_checkpoint_before_build(self) -> None:
        cp = self.builder.create_checkpoint("manual", "Test")
        assert cp is None  # No project state yet

    def test_rollback_before_build(self) -> None:
        result = self.builder.rollback("nonexistent")
        assert result is not None
        assert not result.success

    def test_impact_analysis(self) -> None:
        self.builder.build("Build a test")
        result = self.builder.impact_analysis("nonexistent")
        assert "task_id" in result

    def test_build_with_config(self) -> None:
        config = ProjectBuilderConfig(
            builder=BuilderConfig(max_concurrent_tasks=5),
            auto_execute=False,
            generate_docs=False,
            generate_deployment=False,
        )
        builder = ProjectBuilder(config=config)
        result = builder.build("Build a test")
        assert result["status"] == "completed"

    def test_build_with_config_disabled(self) -> None:
        config = ProjectBuilderConfig(
            builder=BuilderConfig(project_root="/tmp/test_builds"),
            auto_execute=False,
            create_checkpoints=False,
            generate_docs=False,
            generate_deployment=False,
        )
        builder = ProjectBuilder(config=config)
        result = builder.build("Build a test")
        assert result["status"] == "completed"
