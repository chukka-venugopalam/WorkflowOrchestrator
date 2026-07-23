"""Tests for DocumentationGenerator."""

from __future__ import annotations

import tempfile
from pathlib import Path

from workflow_orchestrator.builder.documentation_generator import DocumentationGenerator
from workflow_orchestrator.builder.data_models import TaskGraph, TaskNode, TaskPriority, TaskStatus


class TestDocumentationGenerator:
    """Tests for DocumentationGenerator."""

    def setup_method(self) -> None:
        self.generator = DocumentationGenerator()

    def _create_graph(self) -> TaskGraph:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        graph.phases = ["foundation"]
        graph.nodes["t1"] = TaskNode(task_id="t1", name="Setup", phase="foundation", priority=TaskPriority.HIGH)
        return graph

    def test_generate_all_returns_doc_set(self) -> None:
        graph = self._create_graph()
        docs = self.generator.generate_all("TestApp", {"vision": "Test"}, {"technology_stack": {}, "folder_structure": [], "services": [], "database": {}}, {}, graph)
        assert docs.readme != ""
        assert docs.changelog != ""
        assert docs.architecture != ""

    def test_readme_contains_project_name(self) -> None:
        graph = self._create_graph()
        docs = self.generator.generate_all("MyApp", {"vision": "My app vision"}, {"technology_stack": {}, "folder_structure": [], "services": [], "database": {}}, {}, graph)
        assert "MyApp" in docs.readme

    def test_changelog_has_version(self) -> None:
        graph = self._create_graph()
        docs = self.generator.generate_all("Test", {"vision": ""}, {"technology_stack": {}, "folder_structure": [], "services": [], "database": {}}, {}, graph)
        assert "1.0.0" in docs.changelog

    def test_project_state_contains_status(self) -> None:
        graph = self._create_graph()
        docs = self.generator.generate_all("Test", {"vision": ""}, {"technology_stack": {}, "folder_structure": [], "services": [], "database": {}}, {}, graph)
        assert "planning" in docs.project_state

    def test_tasks_doc(self) -> None:
        graph = self._create_graph()
        docs = self.generator.generate_all("Test", {"vision": ""}, {"technology_stack": {}, "folder_structure": [], "services": [], "database": {}}, {}, graph)
        assert "Setup" in docs.tasks

    def test_write_all_files(self) -> None:
        graph = self._create_graph()
        docs = self.generator.generate_all("Test", {"vision": ""}, {"technology_stack": {}, "folder_structure": [], "services": [], "database": {}}, {}, graph)
        temp_dir = tempfile.mkdtemp()
        paths = self.generator.write_all(docs, temp_dir)
        assert len(paths) > 0
        for p in paths:
            assert Path(p).exists()

    def test_write_all_creates_readme(self) -> None:
        graph = self._create_graph()
        docs = self.generator.generate_all("Test", {"vision": ""}, {"technology_stack": {}, "folder_structure": [], "services": [], "database": {}}, {}, graph)
        temp_dir = tempfile.mkdtemp()
        paths = self.generator.write_all(docs, temp_dir)
        readme_paths = [p for p in paths if "README" in p]
        assert len(readme_paths) > 0

    def test_update_readme(self) -> None:
        temp_dir = tempfile.mkdtemp()
        readme_path = Path(temp_dir) / "README.md"
        self.generator.update_readme(readme_path, "# New Content")
        assert readme_path.exists()
        assert readme_path.read_text() == "# New Content"

    def test_update_changelog_new(self) -> None:
        temp_dir = tempfile.mkdtemp()
        changelog_path = Path(temp_dir) / "CHANGELOG.md"
        self.generator.update_changelog(changelog_path, "## [1.1.0]")
        assert changelog_path.exists()
        content = changelog_path.read_text()
        assert "1.1.0" in content
