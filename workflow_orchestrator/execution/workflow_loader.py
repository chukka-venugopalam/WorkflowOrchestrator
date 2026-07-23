"""Workflow loader — loads workflow definitions from various formats.

Supports:
- YAML (``.yaml``, ``.yml``)
- JSON (``.json``)
- Future DSL extension point
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.models import WorkflowDefinition

logger = logging.getLogger(__name__)


class WorkflowLoader:
    """Loads workflow definitions from files in various formats.

    Supports auto-detection of format based on file extension.
    New format handlers can be registered via ``register_handler()``.

    Usage:
        >>> loader = WorkflowLoader()
        >>> workflow = loader.load("workflows/example.yaml")
        >>> print(workflow.name)
    """

    def __init__(self) -> None:
        self._handlers: dict[str, LoadHandler] = {
            ".yaml": self._load_yaml,
            ".yml": self._load_yaml,
            ".json": self._load_json,
        }

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(
        self,
        path: Path | str,
        format_hint: str | None = None,
    ) -> WorkflowDefinition:
        """Load a workflow definition from a file.

        Args:
            path: Path to the workflow file.
            format_hint: Optional format override (``yaml``, ``json``).
                Auto-detected from extension if not provided.

        Returns:
            A WorkflowDefinition.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the format is unsupported or parsing fails.
        """
        file_path = Path(path).expanduser().resolve()

        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        # Detect format
        if format_hint:
            ext = f".{format_hint.lower()}"
        else:
            ext = file_path.suffix.lower()

        handler = self._handlers.get(ext)
        if handler is None:
            raise ValueError(
                f"Unsupported workflow format '{ext}'. "
                f"Supported: {', '.join(self._handlers.keys())}"
            )

        try:
            workflow = handler(file_path)
            logger.info("Loaded workflow '%s' from %s", workflow.name, file_path)
            return workflow
        except Exception as exc:
            logger.error("Failed to load workflow from %s: %s", file_path, exc)
            raise

    def loads(self, content: str, format: str = "yaml") -> WorkflowDefinition:
        """Load a workflow definition from a string.

        Args:
            content: The workflow content string.
            format: Format of the content (``yaml`` or ``json``).

        Returns:
            A WorkflowDefinition.

        Raises:
            ValueError: If the format is unsupported or parsing fails.
        """
        import yaml

        if format == "yaml":
            data: dict[str, Any] = yaml.safe_load(content)
        elif format == "json":
            data = json.loads(content)
        else:
            raise ValueError(f"Unsupported format '{format}'")

        if not data:
            raise ValueError("Empty workflow content")

        # Build a temporary WorkflowDefinition from the raw data
        # We need to reverse-engineer from the raw data structure
        return self._dict_to_workflow(data)

    # ------------------------------------------------------------------
    # Format handlers
    # ------------------------------------------------------------------

    def _load_yaml(self, path: Path) -> WorkflowDefinition:
        """Load a YAML workflow file.

        Args:
            path: Path to the YAML file.

        Returns:
            A WorkflowDefinition.
        """
        return WorkflowDefinition.from_yaml(path)

    def _load_json(self, path: Path) -> WorkflowDefinition:
        """Load a JSON workflow file.

        Args:
            path: Path to the JSON file.

        Returns:
            A WorkflowDefinition.
        """
        import yaml

        data = json.loads(path.read_text(encoding="utf-8"))
        return self._dict_to_workflow(data, source=str(path))

    def _dict_to_workflow(
        self,
        data: dict[str, Any],
        source: str = "",
    ) -> WorkflowDefinition:
        """Convert a parsed dictionary to a WorkflowDefinition.

        Args:
            data: The parsed workflow data.
            source: Optional source file path.

        Returns:
            A WorkflowDefinition.
        """
        # Create a YAML representation and delegate to from_yaml-like logic
        # This ensures consistency with the YAML format
        import yaml

        name = data.get("name", "Untitled Workflow")
        description = data.get("description", "")
        tags = data.get("tags", [])
        schedule = data.get("schedule")
        raw_steps = data.get("steps", [])

        if not isinstance(raw_steps, list):
            raise ValueError("Workflow 'steps' must be a list")

        # Use WorkflowDefinition.from_yaml logic by round-tripping through YAML
        yaml_data = {
            "name": name,
            "description": description,
            "steps": raw_steps,
            "tags": tags,
        }
        if schedule:
            yaml_data["schedule"] = schedule

        # Parse step data using WorkflowStep.from_dict
        from workflow_orchestrator.models import WorkflowStep

        steps = [WorkflowStep.from_dict(step) for step in raw_steps]

        return WorkflowDefinition(
            name=name,
            description=description,
            steps=steps,
            source=source,
            tags=tags,
            schedule=schedule,
        )

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handler(
        self,
        extension: str,
        handler: LoadHandler,
    ) -> None:
        """Register a custom format handler.

        Args:
            extension: File extension including the dot (e.g., ``.toml``).
            handler: Callable that takes a Path and returns WorkflowDefinition.
        """
        ext = extension if extension.startswith(".") else f".{extension}"
        self._handlers[ext.lower()] = handler
        logger.debug("Registered loader for '%s' format", ext)

    def supported_formats(self) -> list[str]:
        """List supported file formats.

        Returns:
            List of file extensions (e.g., ``.yaml``, ``.json``).
        """
        return list(self._handlers.keys())


# Type alias for load handlers
LoadHandler = Any  # Callable[[Path], WorkflowDefinition]
