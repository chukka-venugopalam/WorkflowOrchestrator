"""Tests for ProjectClassifier."""

from __future__ import annotations

from workflow_orchestrator.builder.project_classifier import ProjectClassifier
from workflow_orchestrator.builder.data_models import ProjectType


class TestProjectClassifier:
    """Tests for ProjectClassifier."""

    def setup_method(self) -> None:
        self.classifier = ProjectClassifier()

    def test_classify_web(self) -> None:
        assert self.classifier.classify("Build a food delivery web app") == ProjectType.WEB
        assert self.classifier.classify("Create a React dashboard") == ProjectType.WEB
        assert self.classifier.classify("Full stack Next.js application") == ProjectType.WEB

    def test_classify_mobile(self) -> None:
        assert self.classifier.classify("iOS and Android mobile app") == ProjectType.MOBILE
        assert self.classifier.classify("Flutter cross-platform app") == ProjectType.MOBILE

    def test_classify_ai(self) -> None:
        assert self.classifier.classify("Build an AI chatbot") == ProjectType.AI
        assert self.classifier.classify("LLM-powered agent system") == ProjectType.AI

    def test_classify_cli(self) -> None:
        assert self.classifier.classify("Command line tool for data processing") == ProjectType.CLI
        assert self.classifier.classify("Build a CLI app") == ProjectType.CLI

    def test_classify_ml(self) -> None:
        assert self.classifier.classify("Machine learning model training pipeline") == ProjectType.ML

    def test_classify_desktop(self) -> None:
        assert self.classifier.classify("Electron desktop app") == ProjectType.DESKTOP

    def test_classify_game(self) -> None:
        assert self.classifier.classify("Unity 3D game engine project") == ProjectType.GAME

    def test_classify_unknown(self) -> None:
        assert self.classifier.classify("Something completely random") == ProjectType.UNKNOWN

    def test_classify_with_project_name(self) -> None:
        result = self.classifier.classify("Web platform for ordering food", "Food Delivery")
        assert result == ProjectType.WEB

    def test_classify_detailed(self) -> None:
        details = self.classifier.classify_detailed("Build a web application with React")
        assert "project_type" in details
        assert "confidence" in details
        assert details["project_type"] == "web"
        assert details["confidence"] > 0

    def test_classify_detailed_unknown(self) -> None:
        details = self.classifier.classify_detailed("xyzzy")
        assert details["project_type"] == "unknown"
        assert details["confidence"] == 0.0

    def test_classify_hybrid(self) -> None:
        result = self.classifier.classify("Full stack web and mobile app")
        assert result == ProjectType.WEB or result == ProjectType.MOBILE

    def test_event_bus_none(self) -> None:
        classifier = ProjectClassifier(event_bus=None)
        assert classifier.classify("web app") == ProjectType.WEB

    def test_empty_description(self) -> None:
        assert self.classifier.classify("") == ProjectType.UNKNOWN
