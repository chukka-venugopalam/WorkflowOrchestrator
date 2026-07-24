"""Plugin Engine — dynamic plugin loader for custom providers, agents, and transports.

Enables expanding system capabilities by adding external plugin packages
to `workflow_orchestrator/plugins/` without modifying core source code.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    name: str
    version: str
    plugin_type: str  # "provider", "agent", "transport", "workflow"
    entry_point: str
    description: str = ""
    author: str = ""
    api_version: str = "1.0.0"


class PluginEngine:
    """Discovers, validates, and loads dynamic plugins at runtime."""

    def __init__(
        self,
        plugins_dir: Optional[str | Path] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.plugins_dir = Path(plugins_dir or Path.cwd() / "workflow_orchestrator" / "plugins")
        self.event_bus = event_bus
        self.loaded_plugins: Dict[str, PluginManifest] = {}

    def discover_and_load(self) -> List[PluginManifest]:
        """Scan plugins directory for `.py` or plugin manifest folders."""
        discovered: List[PluginManifest] = []
        if not self.plugins_dir.exists():
            try:
                self.plugins_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            return discovered

        for item in self.plugins_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                manifest = self._load_manifest(item / "manifest.json")
                if manifest:
                    discovered.append(manifest)
                    self.loaded_plugins[manifest.name] = manifest
            elif item.suffix == ".py" and not item.name.startswith("_"):
                manifest = PluginManifest(
                    name=item.stem,
                    version="1.0.0",
                    plugin_type="custom",
                    entry_point=str(item),
                    description=f"Custom python plugin {item.name}",
                )
                discovered.append(manifest)
                self.loaded_plugins[manifest.name] = manifest

        if self.event_bus:
            self.event_bus.publish(
                Event(
                    type="plugin.discovery_completed",
                    data={"count": len(discovered), "plugins": [p.name for p in discovered]},
                )
            )
        return discovered

    def _load_manifest(self, manifest_path: Path) -> Optional[PluginManifest]:
        try:
            import json
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return PluginManifest(
                    name=data.get("name", manifest_path.parent.name),
                    version=data.get("version", "1.0.0"),
                    plugin_type=data.get("plugin_type", "custom"),
                    entry_point=data.get("entry_point", ""),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    api_version=data.get("api_version", "1.0.0"),
                )
        except Exception as exc:
            logger.warning("Failed to load plugin manifest at %s: %s", manifest_path, exc)
            return None
