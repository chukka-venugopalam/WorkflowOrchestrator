"""Knowledge loader — loads knowledge entries from files.

Supports loading from:
- YAML files (.yaml, .yml)
- JSON files (.json)
- Markdown files (.md) with frontmatter
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.knowledge.knowledge_models import KnowledgeCategory, KnowledgeEntry

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    """Loads knowledge entries from files.

    Usage:
        >>> loader = KnowledgeLoader()
        >>> entries = loader.load_directory(Path("./knowledge/"))
        >>> for entry in entries:
        ...     kb.add(entry.title, entry.content, entry.category)
    """

    def load_file(self, path: Path | str) -> list[KnowledgeEntry]:
        """Load knowledge entries from a single file.

        Args:
            path: Path to the file.

        Returns:
            List of KnowledgeEntry objects.

        Raises:
            ValueError: If the file format is unsupported.
        """
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            logger.warning("Knowledge file not found: %s", file_path)
            return []

        ext = file_path.suffix.lower()

        if ext in (".yaml", ".yml"):
            return self._load_yaml(file_path)
        elif ext == ".json":
            return self._load_json(file_path)
        elif ext == ".md":
            return self._load_markdown(file_path)
        else:
            logger.warning("Unsupported knowledge file format: %s", ext)
            return []

    def load_directory(self, directory: Path | str, recursive: bool = True) -> list[KnowledgeEntry]:
        """Load all knowledge entries from a directory.

        Args:
            directory: Directory path.
            recursive: Whether to scan subdirectories.

        Returns:
            List of all loaded KnowledgeEntry objects.
        """
        dir_path = Path(directory).expanduser().resolve()
        if not dir_path.exists() or not dir_path.is_dir():
            logger.warning("Knowledge directory not found: %s", dir_path)
            return []

        pattern = "**/*" if recursive else "*"
        entries: list[KnowledgeEntry] = []

        for file_path in sorted(dir_path.glob(f"{pattern}.yaml")):
            entries.extend(self.load_file(file_path))
        for file_path in sorted(dir_path.glob(f"{pattern}.yml")):
            entries.extend(self.load_file(file_path))
        for file_path in sorted(dir_path.glob(f"{pattern}.json")):
            entries.extend(self.load_file(file_path))
        for file_path in sorted(dir_path.glob(f"{pattern}.md")):
            entries.extend(self.load_file(file_path))

        logger.info("Loaded %d knowledge entries from %s", len(entries), directory)
        return entries

    def _load_yaml(self, path: Path) -> list[KnowledgeEntry]:
        """Load entries from a YAML file."""
        try:
            import yaml
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except ImportError:
            logger.error("PyYAML is required to load YAML knowledge files")
            return []

        if not data:
            return []

        # Single entry or list of entries
        if isinstance(data, dict):
            return [self._dict_to_entry(data, source=str(path))]
        elif isinstance(data, list):
            return [self._dict_to_entry(item, source=str(path)) for item in data if isinstance(item, dict)]
        return []

    def _load_json(self, path: Path) -> list[KnowledgeEntry]:
        """Load entries from a JSON file."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in %s: %s", path, exc)
            return []

        if isinstance(data, dict):
            return [self._dict_to_entry(data, source=str(path))]
        elif isinstance(data, list):
            return [self._dict_to_entry(item, source=str(path)) for item in data if isinstance(item, dict)]
        return []

    def _load_markdown(self, path: Path) -> list[KnowledgeEntry]:
        """Load entries from a Markdown file.

        Supports optional YAML frontmatter:
        ---
        title: My Knowledge
        category: coding_standard
        tags: [python, style]
        ---
        Content here...
        """
        content = path.read_text(encoding="utf-8")
        metadata: dict[str, Any] = {}
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    metadata = yaml.safe_load(parts[1]) or {}
                    body = parts[2].strip()
                except (ImportError, yaml.YAMLError):
                    body = content

        return [KnowledgeEntry(
            entry_id="",
            title=metadata.get("title", path.stem),
            content=body,
            category=self._parse_category(metadata.get("category", "general")),
            tags=metadata.get("tags", []),
            source=str(path),
        )]

    def _dict_to_entry(self, data: dict[str, Any], source: str = "") -> KnowledgeEntry:
        """Convert a dict to a KnowledgeEntry."""
        import uuid
        return KnowledgeEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:12]),
            title=data.get("title", data.get("name", "Untitled")),
            content=data.get("content", data.get("body", "")),
            category=self._parse_category(data.get("category", "general")),
            tags=data.get("tags", []),
            source=data.get("source", source),
            version=data.get("version", "1.0.0"),
        )

    def _parse_category(self, value: str) -> KnowledgeCategory:
        """Parse a category string to enum."""
        try:
            return KnowledgeCategory(value)
        except ValueError:
            return KnowledgeCategory.GENERAL
