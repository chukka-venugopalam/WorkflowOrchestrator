"""Dependency Detector — detects project dependencies and frameworks.

Detects:
Languages, Frameworks, Databases, Cloud providers, Build tools, CI/CD, Package managers
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
class DependencyInfo:
    """Information about detected project dependencies.

    Attributes:
        languages: Programming languages detected.
        frameworks: Frameworks detected.
        databases: Databases referenced.
        cloud_providers: Cloud providers referenced.
        build_tools: Build tools detected.
        ci_cd: CI/CD platforms detected.
        package_managers: Package managers detected.
        test_frameworks: Test frameworks detected.
        total_dependencies: Total dependency count.
    """

    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    cloud_providers: list[str] = field(default_factory=list)
    build_tools: list[str] = field(default_factory=list)
    ci_cd: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    test_frameworks: list[str] = field(default_factory=list)
    total_dependencies: int = 0


class DependencyDetector:
    """Detects project dependencies by analyzing configuration files.

    Scans package.json, requirements.txt, Cargo.toml, etc. to
    determine the project's dependency profile.

    Usage:
        >>> detector = DependencyDetector()
        >>> deps = detector.detect(".")
        >>> print(f"{deps.languages}: {deps.total_dependencies} deps")
    """

    # Known database package names
    _DATABASES: dict[str, str] = {
        "postgresql": "PostgreSQL", "pg": "PostgreSQL", "psycopg2": "PostgreSQL",
        "mysql": "MySQL", "mysql2": "MySQL", "sqlite": "SQLite", "sqlite3": "SQLite",
        "mongodb": "MongoDB", "mongoose": "MongoDB", "pymongo": "MongoDB",
        "redis": "Redis", "ioredis": "Redis",
        "elasticsearch": "Elasticsearch",
        "cassandra": "Cassandra", "cql": "Cassandra",
        "dynamodb": "DynamoDB", "boto3": "AWS",
        "firebase": "Firebase", "firebase-admin": "Firebase",
        "supabase": "Supabase",
        "prisma": "Prisma", "typeorm": "TypeORM", "sqlalchemy": "SQLAlchemy",
    }

    # Known cloud provider package names
    _CLOUD_PROVIDERS: dict[str, str] = {
        "aws": "AWS", "boto3": "AWS", "aws-sdk": "AWS",
        "azure": "Azure", "@azure": "Azure",
        "gcp": "GCP", "@google-cloud": "GCP",
        "vercel": "Vercel", "@vercel": "Vercel",
        "netlify": "Netlify", "@netlify": "Netlify",
        "cloudflare": "Cloudflare",
        "heroku": "Heroku",
        "railway": "Railway",
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Dependency Detector.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    def detect(self, path: str | Path = ".") -> DependencyInfo:
        """Detect project dependencies.

        Args:
            path: Path to the project directory.

        Returns:
            DependencyInfo with detected dependencies.
        """
        root = Path(path).expanduser().resolve()
        info = DependencyInfo()

        # Check package.json
        package_json = root / "package.json"
        if package_json.exists():
            self._detect_from_package_json(package_json, info)

        # Check requirements.txt
        req_file = root / "requirements.txt"
        if req_file.exists():
            self._detect_from_requirements_txt(req_file, info)

        # Check Cargo.toml
        cargo_file = root / "Cargo.toml"
        if cargo_file.exists():
            info.languages.append("Rust")
            info.total_dependencies += self._count_toml_deps(cargo_file)

        # Check go.mod
        go_mod = root / "go.mod"
        if go_mod.exists():
            info.languages.append("Go")
            deps = go_mod.read_text(encoding="utf-8").count("\nrequire")
            info.total_dependencies += deps

        # Check pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            info.languages.append("Python")
            content = pyproject.read_text(encoding="utf-8")
            info.total_dependencies += content.count("dependencies") + content.count("dev-dependencies")

        # Detect CI/CD
        self._detect_cicd(root, info)

        return info

    def _detect_from_package_json(self, file_path: Path, info: DependencyInfo) -> None:
        """Detect dependencies from package.json.

        Args:
            file_path: Path to package.json.
            info: DependencyInfo to update.
        """
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            all_deps = {
                **data.get("dependencies", {}),
                **data.get("devDependencies", {}),
                **data.get("peerDependencies", {}),
            }

            info.languages.append("JavaScript/TypeScript")
            info.total_dependencies = len(all_deps)

            # Detect package manager
            if (file_path.parent / "pnpm-lock.yaml").exists():
                info.package_managers.append("pnpm")
            elif (file_path.parent / "yarn.lock").exists():
                info.package_managers.append("Yarn")
            elif (file_path.parent / "package-lock.json").exists():
                info.package_managers.append("npm")
            elif (file_path.parent / "bun.lockb").exists():
                info.package_managers.append("Bun")

            # Detect databases
            for pkg, db_name in self._DATABASES.items():
                if any(pkg in dep for dep in all_deps):
                    if db_name not in info.databases:
                        info.databases.append(db_name)

            # Detect cloud providers
            for pkg, cloud_name in self._CLOUD_PROVIDERS.items():
                if any(pkg in dep for dep in all_deps):
                    if cloud_name not in info.cloud_providers:
                        info.cloud_providers.append(cloud_name)

            # Detect test frameworks
            test_pkgs = ["jest", "vitest", "mocha", "chai", "cypress", "playwright", "puppeteer", "ava", "tap"]
            for pkg in test_pkgs:
                if pkg in all_deps:
                    info.test_frameworks.append(pkg.capitalize())

            # Detect build tools
            build_pkgs = ["webpack", "vite", "rollup", "esbuild", "parcel", "tsc", "babel", "swc"]
            for pkg in build_pkgs:
                if pkg in all_deps:
                    info.build_tools.append(pkg.capitalize())

        except Exception:
            pass

    def _detect_from_requirements_txt(self, file_path: Path, info: DependencyInfo) -> None:
        """Detect dependencies from requirements.txt.

        Args:
            file_path: Path to requirements.txt.
            info: DependencyInfo to update.
        """
        try:
            content = file_path.read_text(encoding="utf-8").lower()
            lines = [line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")]
            info.languages.append("Python")
            info.total_dependencies += len(lines)

            for line in lines:
                pkg = line.split("=")[0].split(">")[0].split("<")[0].split("~")[0].strip()
                if pkg in ["flask", "django", "fastapi", "bottle", "tornado"]:
                    info.frameworks.append(pkg.capitalize())
                if pkg == "pytest":
                    info.test_frameworks.append("Pytest")

        except Exception:
            pass

    def _count_toml_deps(self, file_path: Path) -> int:
        """Count dependencies in a Cargo.toml file.

        Args:
            file_path: Path to Cargo.toml.

        Returns:
            Count of dependencies.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            count = 0
            in_deps = False
            for line in content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("[dependencies"):
                    in_deps = True
                    continue
                if stripped.startswith("[") and in_deps:
                    break
                if in_deps and "=" in stripped:
                    count += 1
            return count
        except Exception:
            return 0

    def _detect_cicd(self, root: Path, info: DependencyInfo) -> None:
        """Detect CI/CD configuration.

        Args:
            root: Project root directory.
            info: DependencyInfo to update.
        """
        github_actions = root / ".github" / "workflows"
        if github_actions.exists():
            info.ci_cd.append("GitHub Actions")

        if (root / ".gitlab-ci.yml").exists():
            info.ci_cd.append("GitLab CI")

        if (root / "Jenkinsfile").exists():
            info.ci_cd.append("Jenkins")

        if (root / "circle.yml").exists() or (root / ".circleci").exists():
            info.ci_cd.append("CircleCI")

        if (root / ".travis.yml").exists():
            info.ci_cd.append("Travis CI")
