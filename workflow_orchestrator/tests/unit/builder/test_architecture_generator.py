"""Tests for ArchitectureGenerator."""

from __future__ import annotations

from workflow_orchestrator.builder.architecture_generator import ArchitectureGenerator
from workflow_orchestrator.builder.data_models import ProjectType


class TestArchitectureGenerator:
    """Tests for ArchitectureGenerator."""

    def setup_method(self) -> None:
        self.generator = ArchitectureGenerator()
        self.requirements = {
            "vision": "Test project",
            "features": [],
            "constraints": [],
        }

    def test_generate_returns_all_keys(self) -> None:
        arch = self.generator.generate(self.requirements, ProjectType.WEB)
        expected_keys = [
            "system_architecture", "folder_structure", "technology_stack",
            "services", "database", "deployment", "external_integrations",
            "interfaces", "dependencies", "communication_flow",
        ]
        for key in expected_keys:
            assert key in arch, f"Missing key: {key}"

    def test_system_architecture_not_empty(self) -> None:
        arch = self.generator.generate(self.requirements, ProjectType.WEB)
        assert len(arch["system_architecture"]) > 0

    def test_folder_structure_list(self) -> None:
        arch = self.generator.generate(self.requirements, ProjectType.WEB)
        assert len(arch["folder_structure"]) > 0

    def test_technology_stack_dict(self) -> None:
        arch = self.generator.generate(self.requirements, ProjectType.WEB)
        assert "language" in arch["technology_stack"]
        assert "framework" in arch["technology_stack"]

    def test_different_types_produce_different_stacks(self) -> None:
        web_arch = self.generator.generate(self.requirements, ProjectType.WEB)
        ai_arch = self.generator.generate(self.requirements, ProjectType.AI)
        assert web_arch["technology_stack"]["language"] != ai_arch["technology_stack"]["language"]

    def test_services_list(self) -> None:
        arch = self.generator.generate(self.requirements, ProjectType.WEB)
        assert len(arch["services"]) > 0
        for service in arch["services"]:
            assert "name" in service
            assert "responsibility" in service

    def test_database_dict(self) -> None:
        arch = self.generator.generate(self.requirements, ProjectType.WEB)
        assert "primary_database" in arch["database"]

    def test_string_project_type(self) -> None:
        arch = self.generator.generate(self.requirements, "web")
        assert "language" in arch["technology_stack"]

    def test_unknown_project_type(self) -> None:
        arch = self.generator.generate(self.requirements, "unknown")
        assert arch["system_architecture"] != ""
