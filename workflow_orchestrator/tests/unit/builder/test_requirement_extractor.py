"""Tests for RequirementExtractor."""

from __future__ import annotations

from workflow_orchestrator.builder.requirement_extractor import RequirementExtractor


class TestRequirementExtractor:
    """Tests for RequirementExtractor."""

    def setup_method(self) -> None:
        self.extractor = RequirementExtractor()

    def test_extract_returns_all_keys(self) -> None:
        reqs = self.extractor.extract("Build a food delivery platform")
        expected_keys = [
            "vision", "objectives", "features", "constraints", "users",
            "functional_requirements", "non_functional_requirements",
            "acceptance_criteria", "risk_list", "questions",
        ]
        for key in expected_keys:
            assert key in reqs, f"Missing key: {key}"

    def test_vision_not_empty(self) -> None:
        reqs = self.extractor.extract("Build a web app")
        assert len(reqs["vision"]) > 0

    def test_objectives_list(self) -> None:
        reqs = self.extractor.extract("Test")
        assert len(reqs["objectives"]) > 0
        assert isinstance(reqs["objectives"], list)

    def test_features_list(self) -> None:
        reqs = self.extractor.extract("Build a web app with login and payments")
        assert len(reqs["features"]) > 0
        for feature in reqs["features"]:
            assert "name" in feature
            assert "description" in feature
            assert "priority" in feature

    def test_features_include_core(self) -> None:
        reqs = self.extractor.extract("Build something")
        names = [f["name"] for f in reqs["features"]]
        assert "Project Setup" in names
        assert "Testing Suite" in names

    def test_constraints_list(self) -> None:
        reqs = self.extractor.extract("Build a web app")
        assert len(reqs["constraints"]) > 0
        for c in reqs["constraints"]:
            assert "category" in c
            assert "description" in c
            assert "severity" in c

    def test_users_list(self) -> None:
        reqs = self.extractor.extract("Build an app")
        assert len(reqs["users"]) > 0
        for user in reqs["users"]:
            assert "role" in user
            assert "description" in user

    def test_functional_requirements(self) -> None:
        reqs = self.extractor.extract("Build an app")
        assert len(reqs["functional_requirements"]) > 0
        for fr in reqs["functional_requirements"]:
            assert "id" in fr
            assert "description" in fr

    def test_non_functional_requirements(self) -> None:
        reqs = self.extractor.extract("Build an app")
        assert len(reqs["non_functional_requirements"]) > 0

    def test_acceptance_criteria(self) -> None:
        reqs = self.extractor.extract("Build a platform")
        assert len(reqs["acceptance_criteria"]) > 0

    def test_risk_list(self) -> None:
        reqs = self.extractor.extract("Build an app")
        assert len(reqs["risk_list"]) > 0

    def test_questions(self) -> None:
        reqs = self.extractor.extract("Build an app")
        assert len(reqs["questions"]) > 0

    def test_project_name_included(self) -> None:
        reqs = self.extractor.extract("Build a delivery platform", "FoodApp")
        assert "FoodApp" in reqs["vision"] or "delivery" in reqs["vision"]

    def test_empty_idea(self) -> None:
        reqs = self.extractor.extract("")
        assert reqs["vision"] != ""
