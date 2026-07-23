"""Documentation Generator — automatically updates project documentation files.

Automatically generates and updates:
- README.md
- CHANGELOG.md
- ARCHITECTURE.md
- PROJECT_STATE.md
- TASKS.md
- API.md
- DECISIONS.md

No manual documentation required.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import (
    DocumentationSet,
    TaskGraph,
)
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class DocumentationGenerator:
    """Generates and updates project documentation automatically.

    Creates documentation based on project requirements, architecture,
    roadmap, task graph, and state.

    Usage:
        >>> generator = DocumentationGenerator()
        >>> docs = generator.generate_all(project_name, requirements, architecture, roadmap, graph)
        >>> generator.write_all(docs, "/path/to/project/docs")
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Documentation Generator.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate_all(
        self,
        project_name: str,
        requirements: dict[str, Any],
        architecture: dict[str, Any],
        roadmap: dict[str, Any],
        task_graph: TaskGraph,
        project_state: Any = None,
    ) -> DocumentationSet:
        """Generate all documentation files.

        Args:
            project_name: The project name.
            requirements: The structured requirements.
            architecture: The architecture specification.
            roadmap: The implementation roadmap.
            task_graph: The task graph.
            project_state: Optional project state.

        Returns:
            A DocumentationSet with all documentation content.
        """
        docs = DocumentationSet(
            project_id=task_graph.project_id,
            readme=self._generate_readme(project_name, requirements, architecture),
            changelog=self._generate_changelog(project_name),
            architecture=self._generate_architecture_doc(project_name, architecture),
            project_state=self._generate_project_state(project_name, project_state),
            tasks=self._generate_tasks_doc(project_name, task_graph),
            api=self._generate_api_doc(project_name, architecture),
            decisions=self._generate_decisions_doc(project_name),
        )

        self._publish_event("builder.documentation_updated", {
            "project_id": task_graph.project_id,
            "project_name": project_name,
            "doc_count": 7,
        })

        logger.info("Generated documentation set for '%s'", project_name)
        return docs

    def _generate_readme(
        self,
        project_name: str,
        requirements: dict[str, Any],
        architecture: dict[str, Any],
    ) -> str:
        """Generate README.md content.

        Args:
            project_name: The project name.
            requirements: The structured requirements.
            architecture: The architecture specification.

        Returns:
            README.md content.
        """
        vision = requirements.get("vision", f"A {project_name} project")
        tech_stack = architecture.get("technology_stack", {})

        return (
            f"# {project_name}\n\n"
            f"## Vision\n\n{vision}\n\n"
            f"## Tech Stack\n\n"
            + "\n".join(f"- **{k.title()}:** {v}" for k, v in tech_stack.items()) + "\n\n"
            f"## Getting Started\n\n"
            f"### Prerequisites\n\n"
            f"- [List prerequisites here]\n\n"
            f"### Installation\n\n"
            f"```bash\n# Clone the repository\ngit clone <repository-url>\ncd {project_name.lower().replace(' ', '-')}\n\n# Install dependencies\n# [Add install command]\n\n# Set up environment\ncp .env.example .env\n# Edit .env with your configuration\n\n# Run the application\n# [Add run command]\n```\n\n"
            f"## Project Structure\n\n"
            f"```\n{self._generate_folder_structure_md(architecture)}\n```\n\n"
            f"## Development\n\n"
            f"- [Development guide](docs/ARCHITECTURE.md)\n"
            f"- [API documentation](docs/API.md)\n"
            f"- [Tasks and progress](docs/TASKS.md)\n\n"
            f"## License\n\nMIT\n"
        )

    def _generate_changelog(self, project_name: str) -> str:
        """Generate CHANGELOG.md content.

        Args:
            project_name: The project name.

        Returns:
            CHANGELOG.md content.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return (
            f"# Changelog\n\n"
            f"## [1.0.0] - {now}\n\n"
            f"### Added\n"
            f"- Initial project setup\n"
            f"- Core architecture implementation\n"
            f"- All foundation features\n\n"
            f"### Changed\n\n"
            f"### Deprecated\n\n"
            f"### Removed\n\n"
            f"### Fixed\n\n"
            f"### Security\n"
        )

    def _generate_architecture_doc(self, project_name: str, architecture: dict[str, Any]) -> str:
        """Generate ARCHITECTURE.md content.

        Args:
            project_name: The project name.
            architecture: The architecture specification.

        Returns:
            ARCHITECTURE.md content.
        """
        return (
            f"# Architecture - {project_name}\n\n"
            f"## System Architecture\n\n{architecture.get('system_architecture', '')}\n\n"
            f"## Folder Structure\n\n```\n"
            + "\n".join(architecture.get("folder_structure", []))
            + "\n```\n\n"
            f"## Technology Stack\n\n"
            + "\n".join(f"- **{k.title()}:** {v}" for k, v in architecture.get("technology_stack", {}).items()) + "\n\n"
            f"## Services\n\n"
            + "\n".join(f"- **{s['name']}:** {s['responsibility']}" for s in architecture.get("services", [])) + "\n\n"
            f"## Database\n\n"
            + f"- Primary: {architecture.get('database', {}).get('primary_database', 'TBD')}\n"
            + f"- Cache: {architecture.get('database', {}).get('cache_layer', 'TBD')}\n\n"
            f"## Communication Flow\n\n{architecture.get('communication_flow', '')}\n\n"
            f"## Deployment\n\n{architecture.get('deployment', {}).get('hosting', 'TBD')}\n"
        )

    def _generate_project_state(self, project_name: str, state: Any) -> str:
        """Generate PROJECT_STATE.md content.

        Args:
            project_name: The project name.
            state: Optional project state.

        Returns:
            PROJECT_STATE.md content.
        """
        status = state.status if state else "planning"
        return (
            f"# Project State - {project_name}\n\n"
            f"**Status:** {status}\n"
            f"**Last Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            f"## Current Phase\n\n{state.current_phase if state else 'Planning'}\n\n"
            f"## Phases\n\n"
            + "\n".join(
                f"- **{name}:** {ps.status}"
                for name, ps in (state.phases.items() if state else [])
            ) + "\n\n"
            f"## Completion\n\n"
            f"See detailed progress in [TASKS.md](TASKS.md)\n"
        )

    def _generate_tasks_doc(self, project_name: str, task_graph: TaskGraph) -> str:
        """Generate TASKS.md content.

        Args:
            project_name: The project name.
            task_graph: The task graph.

        Returns:
            TASKS.md content.
        """
        content = f"# Tasks - {project_name}\n\n"
        content += f"Total Tasks: {len(task_graph.nodes)}\n"
        content += f"Dependencies: {len(task_graph.edges)}\n\n"

        for phase in task_graph.phases:
            phase_tasks = [n for n in task_graph.nodes.values() if n.phase == phase]
            content += f"## {phase.replace('_', ' ').title()}\n\n"
            content += "| Task | Priority | Status | Dependencies |\n"
            content += "|------|----------|--------|-------------|\n"
            for task in phase_tasks:
                deps = ", ".join(task.dependencies) if task.dependencies else "—"
                content += f"| {task.name} | {task.priority.value} | {task.status.value} | {deps} |\n"
            content += "\n"

        return content

    def _generate_api_doc(self, project_name: str, architecture: dict[str, Any]) -> str:
        """Generate API.md content.

        Args:
            project_name: The project name.
            architecture: The architecture specification.

        Returns:
            API.md content.
        """
        return (
            f"# API Documentation - {project_name}\n\n"
            f"## Overview\n\n"
            f"API endpoints and interfaces for {project_name}.\n\n"
            f"## Authentication\n\n"
            f"All API requests require authentication via JWT token.\n\n"
            f"## Endpoints\n\n"
            f"### [Endpoint details to be documented]\n\n"
            f"## Error Handling\n\n"
            f"All errors return a standardized JSON response.\n\n"
            f"## Rate Limiting\n\n"
            f"API rate limits apply as configured.\n"
        )

    def _generate_decisions_doc(self, project_name: str) -> str:
        """Generate DECISIONS.md content.

        Args:
            project_name: The project name.

        Returns:
            DECISIONS.md content.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return (
            f"# Decisions - {project_name}\n\n"
            f"## Decision Log\n\n"
            f"| Date | Decision | Rationale |\n"
            f"|------|----------|----------|\n"
            f"| {now} | Project initiated | Automated project generation |\n"
            f"| {now} | Architecture selected | Based on project requirements |\n"
        )

    def _generate_folder_structure_md(self, architecture: dict[str, Any]) -> str:
        """Generate folder structure in markdown format.

        Args:
            architecture: The architecture specification.

        Returns:
            Folder structure as markdown string.
        """
        folders = architecture.get("folder_structure", [])
        lines: list[str] = []
        for item in folders:
            indent = "  " * (item.count("  "))
            lines.append(f"{indent}{item.strip('/')}/" if item.endswith("/") else f"{indent}{item}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def write_all(self, docs: DocumentationSet, output_dir: str | Path) -> list[str]:
        """Write all documentation files to disk.

        Args:
            docs: The documentation set to write.
            output_dir: Directory to write docs to.

        Returns:
            List of written file paths.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        written: list[str] = []

        doc_files: list[tuple[str, str]] = [
            ("README.md", docs.readme),
            ("CHANGELOG.md", docs.changelog),
            ("ARCHITECTURE.md", docs.architecture),
            ("PROJECT_STATE.md", docs.project_state),
            ("TASKS.md", docs.tasks),
            ("API.md", docs.api),
            ("DECISIONS.md", docs.decisions),
        ]

        for filename, content in doc_files:
            if content:
                filepath = output_path / filename
                filepath.write_text(content, encoding="utf-8")
                written.append(str(filepath))
                logger.debug("Written documentation: %s", filepath)

        # Write additional docs
        for name, content in docs.additional.items():
            if content:
                filepath = output_path / name
                filepath.write_text(content, encoding="utf-8")
                written.append(str(filepath))

        logger.info("Written %d documentation files", len(written))
        return written

    def update_readme(self, path: str | Path, content: str) -> None:
        """Update the README.md file.

        Args:
            path: Path to README.md.
            content: New content.
        """
        Path(path).write_text(content, encoding="utf-8")

    def update_changelog(self, path: str | Path, entry: str) -> None:
        """Add a changelog entry.

        Args:
            path: Path to CHANGELOG.md.
            entry: New changelog entry.
        """
        changelog_path = Path(path)
        existing = changelog_path.read_text(encoding="utf-8") if changelog_path.exists() else "# Changelog\n\n"
        # Insert entry after the header
        lines = existing.split("\n")
        insert_pos = 1 if len(lines) > 1 else len(lines)
        lines.insert(insert_pos, f"\n{entry}\n")
        changelog_path.write_text("\n".join(lines), encoding="utf-8")

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="documentation_generator",
            ))
        except Exception:
            pass
