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

from workflow_orchestrator.builder.data_models import ProjectType
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ArchitectureGenerator:
    """Generates architecture specifications from requirements.

    Produces a complete architecture document with folder structure,
    technology recommendations, service boundaries, and data flow.

    Usage:
        >>> generator = ArchitectureGenerator()
        >>> arch = generator.generate(requirements, ProjectType.WEB)
        >>> print(arch["folder_structure"])
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
            "  middleware/",
            "public/",
            "tests/",
            "  unit/",
            "  integration/",
            "  e2e/",
            "scripts/",
            "config/",
            "docs/",
            "docker/",
        ],
        "mobile": [
            "app/",
            "  screens/",
            "  components/",
            "  navigation/",
            "  services/",
            "  store/",
            "  utils/",
            "  assets/",
            "  styles/",
            "  hooks/",
            "  types/",
            "ios/",
            "android/",
            "tests/",
            "  unit/",
            "  integration/",
            "scripts/",
            "docs/",
        ],
        "cli": [
            "cli/",
            "  commands/",
            "  utils/",
            "  config/",
            "  output/",
            "lib/",
            "  core/",
            "  services/",
            "  models/",
            "tests/",
            "  unit/",
            "  integration/",
            "scripts/",
            "docs/",
        ],
        "ai": [
            "app/",
            "  api/",
            "  agents/",
            "  tools/",
            "  memory/",
            "  config/",
            "models/",
            "  prompts/",
            "  chains/",
            "  embeddings/",
            "services/",
            "  llm/",
            "  vector_store/",
            "  monitoring/",
            "data/",
            "  knowledge/",
            "  context/",
            "tests/",
            "  unit/",
            "  integration/",
            "scripts/",
            "docs/",
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
    ) -> dict[str, Any]:
        """Generate a complete architecture specification.

        Args:
            requirements: Structured requirements from RequirementExtractor.
            project_type: The classified project type.

        Returns:
            Dict with architecture specification keys.
        """
        if isinstance(project_type, str):
            try:
                project_type = ProjectType(project_type)
            except ValueError:
                project_type = ProjectType.UNKNOWN

        type_str = project_type.value if isinstance(project_type, ProjectType) else project_type

        architecture: dict[str, Any] = {
            "system_architecture": self._generate_system_architecture(type_str),
            "folder_structure": self._generate_folder_structure(type_str),
            "technology_stack": self._generate_tech_stack(type_str, requirements),
            "services": self._generate_services(type_str, requirements),
            "database": self._generate_database(type_str),
            "deployment": self._generate_deployment(type_str),
            "external_integrations": self._generate_integrations(requirements),
            "interfaces": self._generate_interfaces(type_str),
            "dependencies": self._generate_dependencies(type_str),
            "communication_flow": self._generate_communication_flow(type_str),
        }

        self._publish_event("builder.architecture_generated", {
            "project_type": type_str,
            "folder_count": len(architecture["folder_structure"]),
            "service_count": len(architecture["services"]),
        })

        logger.info("Generated architecture for project type '%s'", type_str)
        return architecture

    def _generate_system_architecture(self, project_type: str) -> str:
        """Generate system architecture description.

        Args:
            project_type: The project type.

        Returns:
            Architecture description string.
        """
        if project_type in ("web", "api"):
            return (
                "Layered architecture with presentation layer (UI components),\n"
                "application layer (services, controllers), domain layer (business logic),\n"
                "and infrastructure layer (database, external services).\n"
                "API gateway handles routing, authentication, and rate limiting.\n"
                "Frontend communicates with backend via RESTful API or GraphQL."
            )
        elif project_type in ("mobile",):
            return (
                "Clean Architecture with presentation layer (screens, widgets),\n"
                "domain layer (use cases, entities), and data layer (repositories, data sources).\n"
                "State management via BLoC/Provider pattern.\n"
                "Network layer with API client, caching, and offline support."
            )
        elif project_type in ("ai", "ml"):
            return (
                "Modular architecture with agent orchestration layer,\n"
                "LLM integration layer, tool/plugin system, memory/persistence layer,\n"
                "and monitoring/observability layer.\n"
                "Vector store for semantic search and knowledge management.\n"
                "Event-driven communication between components."
            )
        return (
            "Clean layered architecture with separation of concerns.\n"
            "Core domain logic isolated from infrastructure concerns.\n"
            "Dependency injection for testability and flexibility."
        )

    def _generate_folder_structure(self, project_type: str) -> list[str]:
        """Generate folder structure based on project type.

        Args:
            project_type: The project type.

        Returns:
            List of folder path strings.
        """
        template = self._FOLDER_TEMPLATES.get(project_type, self._FOLDER_TEMPLATES.get("web", []))
        # Always add root-level files
        root_files = [
            "README.md",
            "CHANGELOG.md",
            "ARCHITECTURE.md",
            "CONTRIBUTING.md",
            "LICENSE",
            ".gitignore",
            ".env.example",
            "package.json" if project_type in ("web", "cli", "api") else "requirements.txt" if project_type in ("ai", "ml") else "Cargo.toml",
        ]
        return root_files + template

    def _generate_tech_stack(self, project_type: str, requirements: dict[str, Any]) -> dict[str, Any]:
        """Generate technology stack recommendations.

        Args:
            project_type: The project type.
            requirements: The structured requirements.

        Returns:
            Dict with tech stack categories.
        """
        stacks: dict[str, dict[str, Any]] = {
            "web": {
                "language": "TypeScript",
                "framework": "Next.js 14+",
                "styling": "Tailwind CSS",
                "state_management": "Zustand / React Query",
                "database": "PostgreSQL + Prisma ORM",
                "api": "Next.js API Routes / tRPC",
                "testing": "Vitest + Playwright",
                "deployment": "Vercel / Docker",
                "ci_cd": "GitHub Actions",
            },
            "mobile": {
                "language": "Dart / TypeScript",
                "framework": "Flutter / React Native",
                "state_management": "Riverpod / Zustand",
                "database": "SQLite (Drift) / Firebase",
                "api": "REST / GraphQL",
                "testing": "Flutter Test / Jest",
                "deployment": "App Store / Google Play",
                "ci_cd": "Codemagic / GitHub Actions",
            },
            "cli": {
                "language": "Python / Rust / TypeScript",
                "framework": "Typer / clap / Commander",
                "testing": "pytest / cargo test / Vitest",
                "deployment": "PyPI / Crates.io / npm",
                "ci_cd": "GitHub Actions",
            },
            "ai": {
                "language": "Python",
                "framework": "LangChain / LlamaIndex",
                "llm_providers": "OpenAI / Anthropic / Open Source",
                "vector_store": "ChromaDB / Pinecone / Qdrant",
                "database": "PostgreSQL",
                "api": "FastAPI",
                "testing": "pytest",
                "deployment": "Docker / Modal / Railway",
            },
        }

        return stacks.get(project_type, stacks.get("web", {}))

    def _generate_services(self, project_type: str, requirements: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate service definitions.

        Args:
            project_type: The project type.
            requirements: The structured requirements.

        Returns:
            List of service dicts.
        """
        common_services = [
            {"name": "Auth Service", "responsibility": "Authentication and authorization", "type": "internal"},
            {"name": "API Gateway", "responsibility": "Request routing and rate limiting", "type": "internal"},
            {"name": "Data Service", "responsibility": "Data persistence and retrieval", "type": "internal"},
            {"name": "Cache Service", "responsibility": "In-memory caching for performance", "type": "internal"},
        ]

        if project_type in ("ai", "ml"):
            common_services.extend([
                {"name": "LLM Service", "responsibility": "AI model inference and prompt management", "type": "internal"},
                {"name": "Vector Store Service", "responsibility": "Embedding storage and semantic search", "type": "internal"},
                {"name": "Agent Service", "responsibility": "Agent orchestration and tool management", "type": "internal"},
            ])

        if project_type in ("web",):
            common_services.extend([
                {"name": "Notification Service", "responsibility": "Email, push, and in-app notifications", "type": "internal"},
                {"name": "File Storage Service", "responsibility": "File upload and content delivery", "type": "internal"},
            ])

        return common_services

    def _generate_database(self, project_type: str) -> dict[str, Any]:
        """Generate database schema description.

        Args:
            project_type: The project type.

        Returns:
            Dict with database design details.
        """
        return {
            "primary_database": "PostgreSQL",
            "cache_layer": "Redis",
            "migration_tool": "Prisma Migrate / Alembic",
            "key_entities": ["users", "sessions", "audit_logs"],
            "indexing_strategy": "B-tree for primary lookups, GIN for full-text search",
            "backup_strategy": "Daily automated backups with point-in-time recovery",
        }

    def _generate_deployment(self, project_type: str) -> dict[str, Any]:
        """Generate deployment architecture.

        Args:
            project_type: The project type.

        Returns:
            Dict with deployment details.
        """
        return {
            "hosting": "Cloud provider (AWS/GCP/Azure) or Vercel/Railway",
            "containerization": "Docker with docker-compose for local dev",
            "orchestration": "Docker Compose / Kubernetes for production",
            "ci_cd": "GitHub Actions with automated testing and deployment",
            "monitoring": "Application monitoring with health checks and logging",
            "rollback_strategy": "Blue-green deployment with automated rollback",
            "scaling": "Horizontal scaling with load balancer",
        }

    def _generate_integrations(self, requirements: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate external integration descriptions.

        Args:
            requirements: The structured requirements.

        Returns:
            List of integration dicts.
        """
        return [
            {"name": "GitHub", "purpose": "Version control and CI/CD", "type": "development"},
            {"name": "Cloud Provider", "purpose": "Hosting and infrastructure", "type": "production"},
            {"name": "Email Service", "purpose": "Transactional emails and notifications", "type": "production"},
        ]

    def _generate_interfaces(self, project_type: str) -> list[dict[str, Any]]:
        """Generate interface definitions.

        Args:
            project_type: The project type.

        Returns:
            List of interface dicts.
        """
        return [
            {"name": "REST API", "description": "HTTP API for client-server communication", "protocol": "HTTP/JSON"},
            {"name": "WebSocket", "description": "Real-time bidirectional communication", "protocol": "WebSocket"},
            {"name": "Database Interface", "description": "Repository pattern for data access", "protocol": "SQL/ORM"},
        ]

    def _generate_dependencies(self, project_type: str) -> list[dict[str, Any]]:
        """Generate dependency list.

        Args:
            project_type: The project type.

        Returns:
            List of dependency dicts.
        """
        return [
            {"name": "Runtime", "description": "Language runtime (Node.js / Python / etc.)"},
            {"name": "Web Framework", "description": "Core web framework"},
            {"name": "Database Driver", "description": "Database connectivity"},
            {"name": "Testing Framework", "description": "Unit and integration testing"},
            {"name": "Linting/Formatting", "description": "Code quality tools"},
        ]

    def _generate_communication_flow(self, project_type: str) -> str:
        """Generate communication flow description.

        Args:
            project_type: The project type.

        Returns:
            Communication flow description.
        """
        return (
            "Client → API Gateway → Service Layer → Data Layer\n"
            "Synchronous: HTTP REST/gRPC for request-response patterns\n"
            "Asynchronous: Message queue for event-driven communication\n"
            "Caching: Redis cache between service and data layers\n"
            "Monitoring: Centralized logging and metrics collection"
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
