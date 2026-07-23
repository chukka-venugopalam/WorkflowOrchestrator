"""Roadmap Generator — creates implementation phases from requirements and architecture.

Produces:
- Milestones with deliverables
- Phase dependencies
- Risk checkpoints
- Estimated complexity ratings
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class RoadmapGenerator:
    """Generates implementation roadmaps from requirements and architecture.

    Creates ordered phases with milestones, deliverables, dependencies,
    and complexity estimates.

    Usage:
        >>> generator = RoadmapGenerator()
        >>> roadmap = generator.generate(requirements, architecture)
        >>> print(len(roadmap["phases"]))
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Roadmap Generator.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        requirements: dict[str, Any],
        architecture: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a complete implementation roadmap.

        Args:
            requirements: Structured requirements from RequirementExtractor.
            architecture: Architecture specification from ArchitectureGenerator.

        Returns:
            Dict with phases, milestones, deliverables, and complexity.
        """
        phases = self._create_phases(requirements, architecture)

        roadmap: dict[str, Any] = {
            "phases": phases,
            "total_phases": len(phases),
            "estimated_complexity": self._estimate_overall_complexity(phases),
            "total_milestones": sum(len(p.get("milestones", [])) for p in phases),
        }

        self._publish_event("builder.roadmap_generated", {
            "phase_count": len(phases),
            "estimated_complexity": roadmap["estimated_complexity"],
        })

        logger.info("Generated roadmap with %d phases", len(phases))
        return roadmap

    def _create_phases(
        self,
        requirements: dict[str, Any],
        architecture: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Create ordered implementation phases.

        Args:
            requirements: Structured requirements.
            architecture: Architecture specification.

        Returns:
            List of phase dicts.
        """
        return [
            {
                "phase": 1,
                "name": "Foundation",
                "description": "Project setup, tooling, and core infrastructure",
                "milestones": [
                    {"name": "Project Initialized", "deliverables": ["Repository created", "CI/CD configured", "Development environment documented"]},
                    {"name": "Core Architecture", "deliverables": ["Folder structure created", "Dependency injection set up", "Configuration system"]},
                ],
                "risk_checkpoints": ["Project structure validated", "Build system verified"],
                "estimated_complexity": "medium",
                "depends_on": [],
                "deliverables": ["Git repository", "Build scripts", "Development environment"],
            },
            {
                "phase": 2,
                "name": "Data Layer",
                "description": "Database schema, models, and data access",
                "milestones": [
                    {"name": "Database Schema", "deliverables": ["Schema designed", "Migrations created", "Seeds implemented"]},
                    {"name": "Data Access", "deliverables": ["Repository layer", "Query optimization", "Caching layer"]},
                ],
                "risk_checkpoints": ["Migration verified", "Query performance tested"],
                "estimated_complexity": "medium",
                "depends_on": [1],
                "deliverables": ["Database schema", "Repository implementation", "Migration scripts"],
            },
            {
                "phase": 3,
                "name": "Core Features",
                "description": "Core business logic and feature implementation",
                "milestones": [
                    {"name": "Core Services", "deliverables": ["Business logic layer", "Service interfaces", "Error handling"]},
                    {"name": "Feature Completion", "deliverables": ["All core features implemented", "Feature tests passing"]},
                ],
                "risk_checkpoints": ["Core features validated", "Integration tests passing"],
                "estimated_complexity": "high",
                "depends_on": [2],
                "deliverables": ["Service implementations", "Feature tests", "Integration tests"],
            },
            {
                "phase": 4,
                "name": "API & Integration",
                "description": "API layer, external integrations, and interfaces",
                "milestones": [
                    {"name": "API Layer", "deliverables": ["API endpoints", "Request validation", "Response formatting"]},
                    {"name": "External Integrations", "deliverables": ["Third-party integrations", "Webhook handlers"]},
                ],
                "risk_checkpoints": ["API contracts verified", "Integration tests pass"],
                "estimated_complexity": "medium",
                "depends_on": [3],
                "deliverables": ["API documentation", "Integration code", "API tests"],
            },
            {
                "phase": 5,
                "name": "Testing & Quality",
                "description": "Comprehensive testing, linting, and quality assurance",
                "milestones": [
                    {"name": "Test Coverage", "deliverables": ["Unit tests", "Integration tests", "E2E tests"]},
                    {"name": "Quality Gates", "deliverables": ["Linting configured", "Type checking", "Code review"]},
                ],
                "risk_checkpoints": ["Coverage threshold met", "All quality gates pass"],
                "estimated_complexity": "medium",
                "depends_on": [4],
                "deliverables": ["Test suite", "Quality reports", "Coverage reports"],
            },
            {
                "phase": 6,
                "name": "Documentation",
                "description": "Complete project documentation",
                "milestones": [
                    {"name": "Technical Docs", "deliverables": ["Architecture documentation", "API reference", "Setup guide"]},
                    {"name": "User Docs", "deliverables": ["User manual", "Deployment guide"]},
                ],
                "risk_checkpoints": ["Documentation reviewed"],
                "estimated_complexity": "low",
                "depends_on": [5],
                "deliverables": ["README.md", "API docs", "Deployment guide"],
            },
            {
                "phase": 7,
                "name": "Deployment",
                "description": "Deployment configuration and release",
                "milestones": [
                    {"name": "Deployment Setup", "deliverables": ["Deployment scripts", "Environment config", "Monitoring setup"]},
                    {"name": "Release", "deliverables": ["Production deployment", "Release notes"]},
                ],
                "risk_checkpoints": ["Deployment verified", "Monitoring operational"],
                "estimated_complexity": "medium",
                "depends_on": [6],
                "deliverables": ["Deployment pipeline", "Monitoring dashboards", "Release notes"],
            },
        ]

    def _estimate_overall_complexity(self, phases: list[dict[str, Any]]) -> str:
        """Estimate overall project complexity.

        Args:
            phases: The implementation phases.

        Returns:
            Complexity rating string.
        """
        complexity_map = {"low": 1, "medium": 2, "high": 3}
        total = sum(complexity_map.get(p.get("estimated_complexity", "medium"), 2) for p in phases)
        avg = total / len(phases) if phases else 0

        if avg >= 2.5:
            return "high"
        elif avg >= 1.5:
            return "medium"
        return "low"

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="roadmap_generator",
            ))
        except Exception:
            pass
