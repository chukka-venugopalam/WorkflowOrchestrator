"""Tests for RoadmapGenerator."""

from __future__ import annotations

from workflow_orchestrator.builder.roadmap_generator import RoadmapGenerator


class TestRoadmapGenerator:
    """Tests for RoadmapGenerator."""

    def setup_method(self) -> None:
        self.generator = RoadmapGenerator()
        self.requirements = {"vision": "Test project", "features": []}
        self.architecture = {
            "technology_stack": {"language": "Python"},
            "services": [],
            "database": {},
        }

    def test_generate_returns_phases(self) -> None:
        roadmap = self.generator.generate(self.requirements, self.architecture)
        assert "phases" in roadmap
        assert len(roadmap["phases"]) > 0

    def test_total_phases(self) -> None:
        roadmap = self.generator.generate(self.requirements, self.architecture)
        assert roadmap["total_phases"] == len(roadmap["phases"])

    def test_each_phase_has_required_fields(self) -> None:
        roadmap = self.generator.generate(self.requirements, self.architecture)
        for phase in roadmap["phases"]:
            assert "phase" in phase
            assert "name" in phase
            assert "description" in phase
            assert "milestones" in phase
            assert "estimated_complexity" in phase
            assert "deliverables" in phase

    def test_estimated_complexity(self) -> None:
        roadmap = self.generator.generate(self.requirements, self.architecture)
        assert roadmap["estimated_complexity"] in ("low", "medium", "high")

    def test_total_milestones(self) -> None:
        roadmap = self.generator.generate(self.requirements, self.architecture)
        assert roadmap["total_milestones"] > 0

    def test_phase_dependencies(self) -> None:
        roadmap = self.generator.generate(self.requirements, self.architecture)
        for phase in roadmap["phases"]:
            assert "depends_on" in phase
            assert isinstance(phase["depends_on"], list)

    def test_first_phase_no_dependencies(self) -> None:
        roadmap = self.generator.generate(self.requirements, self.architecture)
        assert roadmap["phases"][0]["depends_on"] == []
