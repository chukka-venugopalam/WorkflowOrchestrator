"""Architecture Generator — creates architecture specification from structured requirements.

Produces:
- System architecture description
- Folder structure
- Technology stack
- Services
- Database schema
- Deployment architecture
- External integrations
- Interfaces
- Dependencies
- Communication flow

Not code — pure architecture specification.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import ProjectScale, ProjectType
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ArchitectureGenerator:
    """Generates architecture specifications from requirements.

    Produces a complete architecture document with folder structure,
    technology recommendations, service boundaries, and data flow.
    """

    # Architecture templates for each project type
    _FOLDER_TEMPLATES: dict[str, list[str]] = {
        "web": [
            "src/",
            "  components/",
            "  pages/",
            "  api/",
            "  lib/",
            "  utils/",
            "  styles/",
            "  hooks/",
            "  types/",
            "public/",
            "tests/",
            "  unit/",
            "  integration/",
            "scripts/",
            "config/",
            "docs/",
        ],
        "mobile": [
            "app/",
            "  screens/",
            "  components/",
            "  services/",
            "  assets/",
            "ios/",
            "android/",
            "tests/",
            "docs/",
        ],
        "cli": [
            "cli/",
            "  commands/",
            "  utils/",
            "lib/",
            "tests/",
            "docs/",
        ],
        "ai": [
            "app/",
            "  api/",
            "  agents/",
            "  tools/",
            "models/",
            "tests/",
            "docs/",
        ],
        "ml": [
            "src/",
            "  data/",
            "  models/",
            "  features/",
            "notebooks/",
            "tests/",
            "docs/",
        ],
        "game": [
            "src/",
            "  entities/",
            "  scenes/",
            "  systems/",
            "assets/",
            "  sprites/",
            "  audio/",
            "tests/",
            "docs/",
        ],
        "desktop": [
            "src/",
            "  ui/",
            "  core/",
            "assets/",
            "packaging/",
            "tests/",
            "docs/",
        ],
        "api": [
            "app/",
            "  api/",
            "  core/",
            "  models/",
            "  services/",
            "tests/",
            "docs/",
        ],
        "library": [
            "src/",
            "tests/",
            "examples/",
            "docs/",
        ],
        "embedded": [
            "firmware/",
            "src/",
            "include/",
            "drivers/",
            "tests/",
        ],
        "robotics": [
            "nodes/",
            "launch/",
            "config/",
            "src/",
            "tests/",
        ],
        "research": [
            "experiments/",
            "data/",
            "src/",
            "results/",
            "docs/",
        ],
        "education": [
            "lessons/",
            "exercises/",
            "src/",
            "tests/",
        ],
        "enterprise": [
            "services/",
            "modules/",
            "common/",
            "infra/",
            "tests/",
        ],
        "infrastructure": [
            "terraform/",
            "kubernetes/",
            "scripts/",
            "tests/",
        ],
        "hybrid": [
            "apps/",
            "services/",
            "shared/",
            "tests/",
        ],
        "generic": [
            "src/",
            "tests/",
            "docs/",
            "config/",
        ],
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Architecture Generator.

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
        project_type: ProjectType | str = ProjectType.UNKNOWN,
        project_scale: ProjectScale | str = ProjectScale.STANDARD,
    ) -> dict[str, Any]:
        """Generate a complete architecture specification.

        Args:
            requirements: Structured requirements from RequirementExtractor.
            project_type: The classified project type.
            project_scale: The classified project scale/complexity.

        Returns:
            Dict with architecture specification keys.
        """
        if isinstance(project_type, str):
            try:
                project_type = ProjectType(project_type)
            except ValueError:
                project_type = ProjectType.UNKNOWN

        if isinstance(project_scale, str):
            try:
                project_scale = ProjectScale(project_scale)
            except ValueError:
                project_scale = ProjectScale.STANDARD

        type_str = project_type.value if isinstance(project_type, ProjectType) else str(project_type)
        scale_str = project_scale.value if isinstance(project_scale, ProjectScale) else str(project_scale)

        architecture: dict[str, Any] = {
            "project_type": type_str,
            "project_scale": scale_str,
            "system_architecture": self._generate_system_architecture(type_str, project_scale),
            "folder_structure": self._generate_folder_structure(type_str, project_scale),
            "technology_stack": self._generate_tech_stack(type_str, requirements, project_scale),
            "services": self._generate_services(type_str, requirements, project_scale),
            "database": self._generate_database(type_str, project_scale),
            "deployment": self._generate_deployment(type_str, project_scale),
            "external_integrations": self._generate_integrations(requirements),
            "interfaces": self._generate_interfaces(type_str, project_scale),
            "dependencies": self._generate_dependencies(type_str, project_scale),
            "communication_flow": self._generate_communication_flow(type_str, project_scale),
        }

        self._publish_event("builder.architecture_generated", {
            "project_type": type_str,
            "project_scale": scale_str,
            "folder_count": len(architecture["folder_structure"]),
            "service_count": len(architecture["services"]),
        })

        logger.info("Generated architecture for project type '%s' / scale '%s'", type_str, scale_str)
        return architecture

    def _generate_system_architecture(self, project_type: str, project_scale: ProjectScale) -> str:
        """Generate system architecture description."""
        if project_scale == ProjectScale.MINIMAL:
            return (
                f"Minimal, standalone single-package architecture for a {project_type} project.\n"
                "Focuses on core functionality in a clean, flat layout without multi-service overhead."
            )

        if project_type in ("web", "api"):
            return (
                "Layered architecture with presentation layer (UI components),\n"
                "application layer (services, controllers), and domain layer.\n"
                "Communicates via HTTP RESTful or GraphQL endpoints."
            )
        elif project_type in ("game",):
            if project_scale == ProjectScale.LARGE:
                return (
                    "Client-server multiplayer game architecture with state synchronization,\n"
                    "matchmaking service, real-time networking (WebSockets/UDP), and leaderboard DB."
                )
            return (
                "Modular game architecture with scene management, entity-component-system (ECS),\n"
                "input handling, rendering pipeline, and local asset storage."
            )
        elif project_type in ("mobile", "desktop"):
            return (
                "Clean Architecture with UI view layer, domain state management,\n"
                "and local data persistence."
            )
        elif project_type in ("ai", "ml"):
            return (
                "Pipeline architecture with model execution layer, prompt/agent tools,\n"
                "and data processing/vector storage."
            )
        return (
            f"Clean modular architecture for {project_type} with separation of concerns\n"
            "and simple component interfaces."
        )

    def _generate_folder_structure(self, project_type: str, project_scale: ProjectScale) -> list[str]:
        """Generate folder structure based on project type and scale."""
        if project_type == "game":
            if project_scale == ProjectScale.MINIMAL:
                template = ["src/", "assets/", "tests/"]
            elif project_scale == ProjectScale.LARGE:
                template = ["client/", "server/", "shared/", "assets/", "tests/", "docker/"]
            else:
                template = self._FOLDER_TEMPLATES["game"]
        elif project_scale == ProjectScale.MINIMAL:
            # Minimal scale uses slim template or generic
            base_temp = self._FOLDER_TEMPLATES.get(project_type, self._FOLDER_TEMPLATES["generic"])
            template = [f for f in base_temp if f.strip().startswith(("src/", "app/", "cli/", "assets/", "tests/"))] or ["src/", "tests/"]
        else:
            template = self._FOLDER_TEMPLATES.get(project_type, self._FOLDER_TEMPLATES["generic"])

        root_files = [
            "README.md",
            "ARCHITECTURE.md",
            ".gitignore",
            "package.json" if project_type in ("web", "cli", "api") else "requirements.txt" if project_type in ("ai", "ml", "game") else "pyproject.toml",
        ]
        return root_files + template

    def _generate_tech_stack(self, project_type: str, requirements: dict[str, Any], project_scale: ProjectScale = ProjectScale.STANDARD) -> dict[str, Any]:
        """Generate technology stack recommendations."""
        stacks: dict[str, dict[str, Any]] = {
            "web": {
                "language": "TypeScript",
                "framework": "Next.js 14+" if project_scale != ProjectScale.MINIMAL else "React / Vite",
                "styling": "Tailwind CSS",
                "state_management": "Zustand",
                "database": "PostgreSQL + Prisma ORM" if project_scale == ProjectScale.LARGE else "SQLite",
                "api": "REST API",
                "testing": "Vitest",
                "deployment": "Vercel / Local",
            },
            "game": {
                "language": "Python" if project_scale == ProjectScale.MINIMAL else "C# / TypeScript",
                "framework": "Pygame / Arcade" if project_scale == ProjectScale.MINIMAL else "Unity / WebGL",
                "rendering": "2D Canvas / Pygame Surface" if project_scale == ProjectScale.MINIMAL else "WebGL / OpenGL",
                "state_management": "Local Game Engine Loop",
                "database": "None (Local File / In-Memory)" if project_scale != ProjectScale.LARGE else "PostgreSQL (Leaderboards)",
                "testing": "pytest",
                "deployment": "Standalone Executable / Local Python script",
            },
            "cli": {
                "language": "Python / Rust",
                "framework": "Typer / Click / clap",
                "testing": "pytest",
                "deployment": "PyPI / Local script",
            },
            "desktop": {
                "language": "Python / TypeScript",
                "framework": "PyQt / Electron / Tauri",
                "testing": "pytest / Vitest",
                "deployment": "PyInstaller / Native Installer",
            },
            "api": {
                "language": "Python / TypeScript",
                "framework": "FastAPI / Express",
                "database": "SQLite" if project_scale == ProjectScale.MINIMAL else "PostgreSQL",
                "testing": "pytest",
                "deployment": "Local Server / Docker",
            },
            "library": {
                "language": "Python / TypeScript",
                "framework": "Standard Package Framework",
                "testing": "pytest / Vitest",
                "deployment": "PyPI / npm",
            },
            "ai": {
                "language": "Python",
                "framework": "LangChain / LlamaIndex",
                "llm_providers": "OpenAI / Anthropic / Local Ollama",
                "vector_store": "ChromaDB",
                "testing": "pytest",
                "deployment": "Local / Docker",
            },
            "ml": {
                "language": "Python",
                "framework": "scikit-learn / PyTorch",
                "testing": "pytest",
                "deployment": "Local / ONNX Runtime",
            },
            "generic": {
                "language": "Python",
                "framework": "Standard Library",
                "testing": "pytest",
                "deployment": "Local execution",
            },
        }

        return stacks.get(project_type, stacks["generic"])

    def _generate_services(self, project_type: str, requirements: dict[str, Any], project_scale: ProjectScale = ProjectScale.STANDARD) -> list[dict[str, Any]]:
        """Generate service definitions."""
        if project_scale == ProjectScale.MINIMAL or (project_type in ("game", "cli", "library") and project_scale != ProjectScale.LARGE):
            return [
                {"name": "Core Application Logic", "responsibility": "Handles primary features and state management", "type": "internal"},
            ]

        services = [
            {"name": "Application Logic", "responsibility": "Core domain rules and state", "type": "internal"},
            {"name": "Data Storage Service", "responsibility": "Local or remote data persistence", "type": "internal"},
        ]

        if project_type in ("web", "api") or project_scale == ProjectScale.LARGE:
            services.extend([
                {"name": "Auth Service", "responsibility": "Authentication and authorization", "type": "internal"},
                {"name": "API Gateway", "responsibility": "Routing and validation", "type": "internal"},
            ])

        return services

    def _generate_database(self, project_type: str, project_scale: ProjectScale = ProjectScale.STANDARD) -> dict[str, Any]:
        """Generate database schema description."""
        if project_scale == ProjectScale.MINIMAL or (project_type in ("game", "cli", "library", "desktop") and project_scale != ProjectScale.LARGE):
            return {
                "primary_database": "None (In-memory / Local File Storage)",
                "cache_layer": "None",
                "migration_tool": "None",
                "key_entities": ["local_state", "user_config"],
                "indexing_strategy": "Direct in-memory access",
                "backup_strategy": "Local file save/load",
            }

        return {
            "primary_database": "PostgreSQL" if project_scale == ProjectScale.LARGE else "SQLite",
            "cache_layer": "Redis" if project_scale == ProjectScale.LARGE else "In-memory LRU",
            "migration_tool": "Alembic / Prisma Migrate",
            "key_entities": ["users", "sessions", "data_records"],
            "indexing_strategy": "B-tree for primary lookups",
            "backup_strategy": "Automated backups",
        }

    def _generate_deployment(self, project_type: str, project_scale: ProjectScale = ProjectScale.STANDARD) -> dict[str, Any]:
        """Generate deployment architecture."""
        if project_scale == ProjectScale.MINIMAL or project_type in ("game", "cli", "library"):
            return {
                "hosting": "Local execution / Standalone binary",
                "containerization": "None required",
                "orchestration": "None",
                "ci_cd": "GitHub Actions",
                "monitoring": "Console logging / Local metrics",
                "rollback_strategy": "Git version control reset",
                "scaling": "Single process execution",
            }

        return {
            "hosting": "Cloud provider (AWS/GCP/Vercel)",
            "containerization": "Docker",
            "orchestration": "Docker Compose / Kubernetes" if project_scale == ProjectScale.LARGE else "Docker Compose",
            "ci_cd": "GitHub Actions",
            "monitoring": "Application logging and health checks",
            "rollback_strategy": "Automated rollback on deployment failure",
            "scaling": "Horizontal scaling" if project_scale == ProjectScale.LARGE else "Vertical scaling",
        }

    def _generate_integrations(self, requirements: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate external integration descriptions."""
        return [
            {"name": "Git", "purpose": "Version control", "type": "development"},
        ]

    def _generate_interfaces(self, project_type: str, project_scale: ProjectScale = ProjectScale.STANDARD) -> list[dict[str, Any]]:
        """Generate interface definitions."""
        if project_type == "game":
            return [
                {"name": "Input Event Interface", "description": "Keyboard/mouse/gamepad event handlers", "protocol": "Event Loop"},
                {"name": "Render Interface", "description": "2D/3D graphics rendering pipeline", "protocol": "Canvas/GPU API"},
            ]
        elif project_type == "cli":
            return [
                {"name": "CLI Argument Parser", "description": "Command line flag and argument parsing", "protocol": "POSIX Standard"},
                {"name": "Terminal Output Interface", "description": "Formatted console output", "protocol": "ANSI / STDOUT"},
            ]
        return [
            {"name": "Application API", "description": "Core interface for component communication", "protocol": "Function calls / HTTP"},
        ]

    def _generate_dependencies(self, project_type: str, project_scale: ProjectScale = ProjectScale.STANDARD) -> list[dict[str, Any]]:
        """Generate dependency list."""
        if project_type == "game":
            return [
                {"name": "Game Engine / GUI Framework", "description": "Pygame / Arcade / Canvas engine"},
                {"name": "Testing Framework", "description": "pytest unit testing framework"},
            ]
        elif project_type == "cli":
            return [
                {"name": "CLI Library", "description": "Typer / Click / Argparse"},
                {"name": "Testing Framework", "description": "pytest"},
            ]
        return [
            {"name": "Runtime", "description": "Python / Node.js runtime"},
            {"name": "Testing Framework", "description": "pytest / Vitest"},
        ]

    def _generate_communication_flow(self, project_type: str, project_scale: ProjectScale = ProjectScale.STANDARD) -> str:
        """Generate communication flow description."""
        if project_type == "game":
            return (
                "User Input → Event Handler → Game Engine Loop → Entity/State Update → Render Pipeline"
            )
        elif project_type == "cli":
            return (
                "Terminal Invocation → Command Parser → Controller Function → Service Logic → Output Formatter"
            )
        return (
            "Client Input → Application Controller → Service Layer → Data Storage"
        )

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="architecture_generator",
            ))
        except Exception:
            pass
