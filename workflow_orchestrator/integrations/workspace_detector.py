"""Workspace Detector — detects the current workspace and determines project type.

Detects:
Next.js, React, Vue, Angular, FastAPI, Flask, Django, Flutter,
Rust, Go, Unity, Unreal, Python Package, Node Package, Java, C#,
Electron, Tauri, Monorepo, and more.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceInfo:
    """Information about a detected workspace/project.

    Attributes:
        root: Project root directory.
        name: Project name.
        type: Detected project type.
        frameworks: Detected frameworks.
        languages: Detected languages.
        package_manager: Detected package manager.
        has_git: Whether git is initialized.
        has_docker: Whether Docker config exists.
        build_tool: Detected build tool.
        test_framework: Detected test framework.
        is_monorepo: Whether it's a monorepo.
    """

    root: str = ""
    name: str = ""
    type: str = ""
    frameworks: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    package_manager: str = ""
    has_git: bool = False
    has_docker: bool = False
    build_tool: str = ""
    test_framework: str = ""
    is_monorepo: bool = False


class WorkspaceDetector:
    """Detects the current workspace and determines project type.

    Scans the project directory for configuration files, dependency
    manifests, and source structure to determine the project type.

    Usage:
        >>> detector = WorkspaceDetector()
        >>> info = detector.detect(".")
        >>> print(f"{info.type}: {info.frameworks}")
    """

    # Project type detection patterns
    _PROJECT_PATTERNS: list[tuple[str, str, list[str], str]] = [
        # (type, language, indicator_files, package_manager)
        ("next.js", "TypeScript", ["next.config.js", "next.config.ts", "next.config.mjs"], "npm"),
        ("react", "TypeScript", ["vite.config.ts", "craco.config.js", "react-app-env.d.ts"], "npm"),
        ("vue", "TypeScript", ["vue.config.js", "nuxt.config.ts", "nuxt.config.js"], "npm"),
        ("angular", "TypeScript", ["angular.json", "tsconfig.json"], "npm"),
        ("fastapi", "Python", ["main.py", "requirements.txt"], "pip"),
        ("flask", "Python", ["app.py", "wsgi.py", "requirements.txt"], "pip"),
        ("django", "Python", ["manage.py", "settings.py", "urls.py"], "pip"),
        ("flutter", "Dart", ["pubspec.yaml"], "pub"),
        ("rust", "Rust", ["Cargo.toml"], "cargo"),
        ("go", "Go", ["go.mod", "go.sum"], "go"),
        ("python-package", "Python", ["setup.py", "setup.cfg", "pyproject.toml"], "pip"),
        ("node-package", "JavaScript", ["package.json"], "npm"),
        ("electron", "TypeScript", ["electron-builder.yml", "electron-main.js"], "npm"),
        ("tauri", "Rust", ["tauri.conf.json", "Cargo.toml"], "cargo"),
        ("unity", "C#", ["Assets/", "ProjectSettings/", "Packages/"], "npm"),
        ("unreal", "C++", ["*.uproject"], "none"),
        ("java", "Java", ["pom.xml", "build.gradle", "build.gradle.kts"], "maven"),
        ("dotnet", "C#", ["*.csproj", "*.sln"], "nuget"),
    ]

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Workspace Detector.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect(self, path: str | Path = ".") -> WorkspaceInfo:
        """Detect workspace information for a given directory.

        Args:
            path: Path to the project directory.

        Returns:
            WorkspaceInfo with detected project details.
        """
        root = Path(path).expanduser().resolve()
        if not root.exists():
            return WorkspaceInfo(root=str(root), name=root.name)

        info = WorkspaceInfo(root=str(root), name=root.name)

        # Detect project type
        ptype, lang, pm = self._detect_project_type(root)
        info.type = ptype
        info.languages = [lang] if lang else []
        info.package_manager = pm

        # Detect frameworks
        info.frameworks = self._detect_frameworks(root)

        # Check git
        info.has_git = (root / ".git").exists()

        # Check Docker
        info.has_docker = any((root / f).exists() for f in ["Dockerfile", "docker-compose.yml", ".dockerignore"])

        # Detect build tool
        info.build_tool = self._detect_build_tool(root)

        # Check monorepo
        info.is_monorepo = self._detect_monorepo(root)

        self._publish_event("integration.workspace_detected", {
            "name": info.name,
            "type": info.type,
            "languages": info.languages,
            "frameworks": info.frameworks,
        })

        return info

    def _detect_project_type(self, root: Path) -> tuple[str, str, str]:
        """Detect the project type from configuration files.

        Args:
            root: Project root directory.

        Returns:
            Tuple of (project_type, language, package_manager).
        """
        for ptype, lang, indicator_files, pm in self._PROJECT_PATTERNS:
            for pattern in indicator_files:
                if "*" in pattern:
                    if list(root.glob(pattern)):
                        return ptype, lang, pm
                elif (root / pattern).exists():
                    return ptype, lang, pm
        return "unknown", "", ""

    def _detect_frameworks(self, root: Path) -> list[str]:
        """Detect frameworks from configuration files.

        Args:
            root: Project root directory.

        Returns:
            List of detected framework names.
        """
        frameworks: list[str] = []

        # Check package.json for frameworks
        package_json = root / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                framework_map = {
                    "next": "Next.js", "react": "React", "vue": "Vue", "angular": "Angular",
                    "svelte": "Svelte", "express": "Express", "fastify": "Fastify",
                    "nestjs": "NestJS", "nuxt": "Nuxt", "gatsby": "Gatsby",
                    "electron": "Electron", "tailwindcss": "Tailwind CSS",
                    "chakra": "Chakra UI", "mui": "Material UI",
                    "jest": "Jest", "vitest": "Vitest", "playwright": "Playwright",
                    "cypress": "Cypress", "prisma": "Prisma", "typeorm": "TypeORM",
                }
                for pkg, name in framework_map.items():
                    if pkg in deps or any(pkg in k for k in deps):
                        frameworks.append(name)
            except Exception:
                pass

        # Check requirements.txt for Python frameworks
        req_file = root / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text(encoding="utf-8").lower()
                python_frameworks = {
                    "flask": "Flask", "django": "Django", "fastapi": "FastAPI",
                    "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic",
                    "pytest": "Pytest", "celery": "Celery", "redis": "Redis",
                }
                for pkg, name in python_frameworks.items():
                    if pkg in content:
                        frameworks.append(name)
            except Exception:
                pass

        return list(set(frameworks))

    def _detect_build_tool(self, root: Path) -> str:
        """Detect the build tool.

        Args:
            root: Project root directory.

        Returns:
            Build tool name.
        """
        build_indicators = {
            "webpack": ["webpack.config.js", "webpack.config.ts"],
            "vite": ["vite.config.ts", "vite.config.js"],
            "rollup": ["rollup.config.js", "rollup.config.ts"],
            "esbuild": ["esbuild.config.js"],
            "turbo": ["turbo.json"],
            "nx": ["nx.json", "workspace.json"],
            "typescript": ["tsconfig.json"],
            "babel": ["babel.config.js", ".babelrc"],
            "make": ["Makefile", "makefile"],
            "cargo": ["Cargo.toml"],
            "gradle": ["build.gradle", "build.gradle.kts"],
            "maven": ["pom.xml"],
        }

        for tool, indicators in build_indicators.items():
            if any((root / f).exists() for f in indicators):
                return tool
        return ""

    def _detect_monorepo(self, root: Path) -> bool:
        """Detect if the project is a monorepo.

        Args:
            root: Project root directory.

        Returns:
            True if it appears to be a monorepo.
        """
        indicators = [
            root / "lerna.json",
            root / "nx.json",
            root / "turbo.json",
            root / "pnpm-workspace.yaml",
        ]
        if any(ind.exists() for ind in indicators):
            return True

        # Check for multiple packages directories
        packages_dirs = list(root.glob("packages/*/package.json"))
        apps_dirs = list(root.glob("apps/*/package.json"))
        return len(packages_dirs) > 1 or len(apps_dirs) > 1

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(type=event_type, data=data, source="workspace_detector"))
        except Exception:
            pass
