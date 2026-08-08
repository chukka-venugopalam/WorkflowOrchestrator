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

from workflow_orchestrator.builder.data_models import ProjectScale, ProjectType
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ProjectClassifier:
    """Classifies project type and scale from a user's natural-language description.

    Uses deterministic keyword matching and pattern recognition to determine the
    most likely project type and scale. Falls back to UNKNOWN if no patterns match,
    and supports provider-assisted or human-in-the-loop disambiguation when inconclusive.
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
            "game engine", "sprite", "physics", "rendering", "sudoku",
            "tic tac toe", "rock paper scissors", "arcade",
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

    _SCALE_DOWN_KEYWORDS: list[str] = [
        "simple", "basic", "small", "just a", "single file", "quick",
        "easy", "tiny", "minimal", "toy", "script", "standalone",
    ]

    _SCALE_UP_KEYWORDS: list[str] = [
        "platform", "multi-user", "multiuser", "scalable", "enterprise",
        "microservice", "microservices", "real-time multiplayer", "multiplayer",
        "dashboard for multiple teams", "distributed", "high-availability",
        "production", "ecosystem", "distributed system", "multi-tier",
    ]

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Project Classifier.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Classification & Scale Estimation
    # ------------------------------------------------------------------

    def estimate_scale(self, description: str, project_name: str = "") -> ProjectScale:
        """Deterministically estimate project scale/complexity tier from text signals.

        Args:
            description: User's project description.
            project_name: Optional project name.

        Returns:
            ProjectScale enum (MINIMAL, STANDARD, LARGE).
        """
        text = f"{project_name} {description}".lower()

        score_up = sum(1 for kw in self._SCALE_UP_KEYWORDS if kw in text)
        score_down = sum(1 for kw in self._SCALE_DOWN_KEYWORDS if kw in text)

        # Explicit scale-up bias
        if score_up >= 2 or any(phrase in text for phrase in ["multiplayer game platform", "dashboard for multiple teams", "distributed system"]):
            return ProjectScale.LARGE

        # Explicit scale-down bias
        if score_down >= 1 and score_up == 0:
            return ProjectScale.MINIMAL

        if score_up >= 1:
            return ProjectScale.LARGE

        return ProjectScale.STANDARD

    def is_inconclusive(self, scores: dict[ProjectType, int]) -> bool:
        """Determine if rule-based classification is inconclusive/ambiguous.

        Condition 1: Result is UNKNOWN (no keywords matched).
        Condition 2: Top two scores are within 20% margin of each other (near tie).
        """
        if not scores:
            return True

        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) < 2:
            return False

        top1 = sorted_scores[0]
        top2 = sorted_scores[1]
        if top1 > 0 and ((top1 - top2) / top1) <= 0.20:
            return True

        return False

    def classify(self, description: str, project_name: str = "") -> ProjectType:
        """Classify the project type from a description.

        Args:
            description: User's natural-language project description.
            project_name: Optional project name for additional context.

        Returns:
            The classified ProjectType.
        """
        text = f"{project_name} {description}".lower()

        scores: dict[ProjectType, int] = {}
        for ptype, keywords in self._KEYWORD_MAPS.items():
            score = sum(len(re.findall(re.escape(kw), text)) for kw in keywords)
            if score > 0:
                scores[ptype] = score

        if not scores:
            result = ProjectType.UNKNOWN
        else:
            result = max(scores, key=scores.get)  # type: ignore[type-var]

        scale = self.estimate_scale(description, project_name)

        self._publish_event("builder.classified", {
            "description": description[:100],
            "project_type": result.value,
            "project_scale": scale.value,
            "scores": {k.value: v for k, v in scores.items()} if scores else {},
        })

        logger.info(
            "Classified project as '%s/%s' (type scores: %s, scale signals: up=%d down=%d)",
            result.value,
            scale.value,
            dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]) if scores else "none",
            sum(1 for kw in self._SCALE_UP_KEYWORDS if kw in text),
            sum(1 for kw in self._SCALE_DOWN_KEYWORDS if kw in text),
        )
        return result

    def classify_with_disambiguation(
        self,
        description: str,
        project_name: str = "",
        provider_manager: Any = None,
        prompt_user_fn: Any = None,
    ) -> tuple[ProjectType, ProjectScale]:
        """Classify project type and scale, delegating to AI provider or human user when inconclusive.

        Args:
            description: User project idea text.
            project_name: Optional project name.
            provider_manager: Optional ProviderManager instance for provider-assisted disambiguation.
            prompt_user_fn: Optional callable for human CLI re-prompting.

        Returns:
            Tuple of (ProjectType, ProjectScale).
        """
        text = f"{project_name} {description}".lower()

        # Step 1: Deterministic keyword scoring
        scores: dict[ProjectType, int] = {}
        for ptype, keywords in self._KEYWORD_MAPS.items():
            score = sum(len(re.findall(re.escape(kw), text)) for kw in keywords)
            if score > 0:
                scores[ptype] = score

        scale = self.estimate_scale(description, project_name)

        # Step 2: Check conclusive condition
        if not self.is_inconclusive(scores):
            primary = max(scores, key=scores.get)  # type: ignore[type-var]
            logger.info(
                "Classified project as '%s/%s' (conclusive rule-based, scores: %s)",
                primary.value,
                scale.value,
                {k.value: v for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]},
            )
            return primary, scale

        # Step 3: Inconclusive -> Attempt Provider-Assisted Disambiguation
        scores_str = {k.value: v for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]} if scores else "none"
        logger.info("Rule-based classification inconclusive (scores: %s) — attempting delegated disambiguation", scores_str)

        if provider_manager is not None:
            try:
                detected = provider_manager.detector.detect_all()
                avail = [p for p in detected if p.available]
                if avail:
                    prompt = (
                        f"Given this project description: '{description}', reply with exactly one project type from this fixed list: "
                        "[web, mobile, desktop, cli, ai, ml, embedded, robotics, research, education, enterprise, game, api, library, infrastructure, hybrid] "
                        "and one scale from [minimal, standard, large]. Reply with only those two words separated by a space."
                    )
                    for prov in avail:
                        try:
                            resp_text = provider_manager.invoke_provider(prov.provider_id, prompt)
                            parsed_type, parsed_scale = self._parse_disambiguation_response(resp_text)
                            if parsed_type != ProjectType.UNKNOWN:
                                logger.info(
                                    "Rule-based classification inconclusive (scores: %s) — delegated disambiguation to desktop provider '%s' (result: %s/%s)",
                                    scores_str,
                                    prov.name,
                                    parsed_type.value,
                                    parsed_scale.value,
                                )
                                return parsed_type, parsed_scale
                        except Exception as exc:
                            logger.warning("Desktop provider '%s' disambiguation attempt failed: %s — trying next candidate", prov.provider_id, exc)
            except Exception as exc:
                logger.warning("Desktop provider disambiguation attempt failed: %s", exc)

        # Step 4: Fallback to Human User Prompt if no provider available or parsing failed
        if prompt_user_fn is not None:
            logger.info("No provider available for disambiguation or parsing failed — prompting human user")
            clarification = prompt_user_fn(description, scores)
            if clarification and clarification.strip():
                # Re-run classification with clarified description
                return self.classify_with_disambiguation(
                    description=f"{description} ({clarification})",
                    project_name=project_name,
                    provider_manager=provider_manager,
                    prompt_user_fn=None,  # Avoid infinite recursion
                )

        # Ultimate fallback if no user prompt handler provided
        primary = max(scores, key=scores.get) if scores else ProjectType.WEB
        logger.warning("Disambiguation unresolved — defaulting to '%s/%s'", primary.value, scale.value)
        return primary, scale

    def _parse_disambiguation_response(self, text: str) -> tuple[ProjectType, ProjectScale]:
        """Defensively parse provider structured reply for type and scale."""
        if not text or not text.strip():
            return ProjectType.UNKNOWN, ProjectScale.STANDARD

        tokens = text.lower().strip().replace(",", " ").replace(".", " ").split()

        found_type = ProjectType.UNKNOWN
        found_scale = ProjectScale.STANDARD

        for token in tokens:
            try:
                pt = ProjectType(token)
                if pt != ProjectType.UNKNOWN:
                    found_type = pt
            except ValueError:
                pass
            try:
                ps = ProjectScale(token)
                found_scale = ps
            except ValueError:
                pass

        return found_type, found_scale

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
