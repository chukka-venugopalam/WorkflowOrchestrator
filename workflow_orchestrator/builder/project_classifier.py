"""Project Classifier — classifies project type from a user's natural-language idea.

Classification is purely rule-based: keywords and patterns in the user's
description determine the project type. No AI reasoning is performed.

Supported types: Web, Mobile, Desktop, CLI, AI, ML, Embedded, Robotics,
Research, Education, Enterprise, Hybrid, Game, API, Library, Infrastructure.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import ProjectType
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ProjectClassifier:
    """Classifies project type from a user's natural-language description.

    Uses keyword matching and pattern recognition to determine the
    most likely project type. Falls back to UNKNOWN if no patterns match.

    Usage:
        >>> classifier = ProjectClassifier()
        >>> ptype = classifier.classify("Build a food delivery web app")
        >>> print(ptype.value)
        'web'
    """

    # Keyword maps for each project type
    _KEYWORD_MAPS: dict[ProjectType, list[str]] = {
        ProjectType.WEB: [
            "web", "website", "web app", "web application", "frontend", "front-end",
            "backend", "back-end", "full stack", "fullstack", "saas", "api",
            "rest api", "graphql", "next.js", "react", "vue", "angular", "svelte",
            "django", "flask", "fastapi", "express", "laravel", "spring",
            "web service", "microservice", "serverless", "landing page",
        ],
        ProjectType.MOBILE: [
            "mobile", "mobile app", "ios", "android", "react native", "flutter",
            "swiftui", "kotlin", "smartphone", "tablet",
            "iphone", "ipad", "play store", "app store", "cross-platform mobile",
        ],
        ProjectType.DESKTOP: [
            "desktop", "electron", "qt", "gtk", "windows app", "mac app",
            "linux app", "native app", "winforms", "wpf", "swing", "javafx",
            "tauri", "cross-platform desktop",
        ],
        ProjectType.CLI: [
            "cli", "command line", "terminal", "shell", "command-line tool",
            "console app", "command", "tui", "terminal ui",
            "cli app", "cli tool", "command-line",
        ],
        ProjectType.AI: [
            "ai", "artificial intelligence", "llm", "chatbot", "gpt",
            "claude", "openai", "langchain", "rag", "retrieval augmented",
            "agent", "vector", "embedding", "natural language", "nlp",
            "conversational", "intelligent", "reasoning",
        ],
        ProjectType.ML: [
            "machine learning", "ml", "deep learning", "neural network",
            "tensorflow", "pytorch", "scikit-learn", "classification",
            "regression", "model training", "inference", "data science",
            "keras", "jupyter", "computer vision", "object detection",
        ],
        ProjectType.EMBEDDED: [
            "embedded", "firmware", "microcontroller", "arduino", "raspberry pi",
            "esp32", "iot", "internet of things", "sensor", "rtos",
            "bare metal", "driver", "hardware",
        ],
        ProjectType.ROBOTICS: [
            "robot", "robotics", "ros", "ros2", "autonomous", "drone",
            "uav", "ugv", "manipulator", "actuator", "motor control",
            "navigation", "slam", "path planning",
        ],
        ProjectType.RESEARCH: [
            "research", "experiment", "simulation", "analysis",
            "scientific", "academic", "paper", "publication", "thesis",
            "prototype", "feasibility", "study",
        ],
        ProjectType.EDUCATION: [
            "education", "learning", "tutorial", "course", "teaching",
            "training", "classroom", "student", "interactive learning",
            "quiz", "assessment", "e-learning", "lms",
        ],
        ProjectType.ENTERPRISE: [
            "enterprise", "erp", "crm", "business", "corporate",
            "dashboard", "analytics", "reporting", "workflow automation",
            "b2b", "sla", "compliance", "audit", "hr", "payroll",
            "inventory", "supply chain",
        ],
        ProjectType.GAME: [
            "game", "gaming", "unity", "unreal", "godot", "2d game",
            "3d game", "rpg", "fps", "puzzle", "multiplayer",
            "game engine", "sprite", "physics", "rendering",
        ],
        ProjectType.API: [
            "api", "rest api", "graphql api", "grpc", "webhook",
            "api gateway", "backend service", "data api", "sdk",
        ],
        ProjectType.LIBRARY: [
            "library", "package", "sdk", "framework", "npm package",
            "pypi", "crate", "gem", "module", "component library",
            "ui library", "utility",
        ],
        ProjectType.INFRASTRUCTURE: [
            "infrastructure", "devops", "ci/cd", "kubernetes", "docker",
            "terraform", "ansible", "cloud", "aws", "azure", "gcp",
            "monitoring", "logging", "deployment", "orchestration",
        ],
        ProjectType.HYBRID: [
            "hybrid", "multi-platform", "cross-platform", "full stack",
            "multi-tier", "n-tier", "distributed system",
        ],
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Project Classifier.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def classify(self, description: str, project_name: str = "") -> ProjectType:
        """Classify the project type from a description.

        Args:
            description: User's natural-language project description.
            project_name: Optional project name for additional context.

        Returns:
            The classified ProjectType.
        """
        # Normalize input
        text = f"{project_name} {description}".lower()

        # Score each project type
        scores: dict[ProjectType, int] = {}
        for ptype, keywords in self._KEYWORD_MAPS.items():
            score = sum(len(re.findall(re.escape(kw), text)) for kw in keywords)
            if score > 0:
                scores[ptype] = score

        # Determine result
        if not scores:
            result = ProjectType.UNKNOWN
        else:
            result = max(scores, key=scores.get)  # type: ignore[type-var]

        self._publish_event("builder.classified", {
            "description": description[:100],
            "project_type": result.value,
            "scores": {k.value: v for k, v in scores.items()} if scores else {},
        })

        logger.info(
            "Classified project as '%s' (scores: %s)",
            result.value,
            dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]) if scores else "none",
        )
        return result

    def classify_detailed(self, description: str, project_name: str = "") -> dict[str, Any]:
        """Classify with detailed scoring information.

        Args:
            description: User's natural-language project description.
            project_name: Optional project name.

        Returns:
            Dict with classification details including type, confidence, and scores.
        """
        text = f"{project_name} {description}".lower()

        scores: dict[str, int] = {}
        for ptype, keywords in self._KEYWORD_MAPS.items():
            score = sum(len(re.findall(re.escape(kw), text)) for kw in keywords)
            if score > 0:
                scores[ptype.value] = score

        # Determine primary type
        if not scores:
            primary = ProjectType.UNKNOWN.value
            confidence = 0.0
        else:
            primary = max(scores, key=scores.get)  # type: ignore[type-var]
            total = sum(scores.values())
            confidence = scores[primary] / total if total > 0 else 0.0

        return {
            "project_type": primary,
            "confidence": round(confidence, 2),
            "scores": scores,
            "is_hybrid": primary == ProjectType.HYBRID.value,
            "matched_keywords": self._get_matched_keywords(primary, text) if primary != ProjectType.UNKNOWN.value else [],
        }

    def _get_matched_keywords(self, project_type_str: str, text: str) -> list[str]:
        """Get which keywords matched for a given project type.

        Args:
            project_type_str: The project type string value.
            text: The normalized description text.

        Returns:
            List of matched keywords.
        """
        try:
            ptype = ProjectType(project_type_str)
        except ValueError:
            return []

        matched: list[str] = []
        for kw in self._KEYWORD_MAPS.get(ptype, []):
            if re.search(re.escape(kw), text):
                matched.append(kw)
        return matched

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish a classifier event if an event bus is available.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="project_classifier",
            ))
        except Exception:
            pass
