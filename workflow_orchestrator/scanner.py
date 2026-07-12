"""Project scanner for automatically detecting project characteristics.

Detects programming languages, frameworks, package managers,
Docker configuration, and Git repository status in a given
directory. Returns structured ``ProjectInfo``.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.models import ProjectInfo

logger = logging.getLogger(__name__)


class ProjectScanner:
    """Scans a directory to detect project characteristics.

    Usage:
        >>> scanner = ProjectScanner()
        >>> info = scanner.scan("/path/to/project")
        >>> print(info.languages)
    """

    # Mapping of indicators to language names
    LANGUAGE_INDICATORS: dict[str, str] = {
        "*.py": "Python",
        "setup.py": "Python",
        "setup.cfg": "Python",
        "pyproject.toml": "Python",
        "requirements.txt": "Python",
        "Pipfile": "Python",
        "*.js": "JavaScript",
        "*.jsx": "JavaScript",
        "*.ts": "TypeScript",
        "*.tsx": "TypeScript",
        "package.json": "JavaScript/Node",
        "*.java": "Java",
        "pom.xml": "Java",
        "build.gradle": "Java",
        "build.gradle.kts": "Java",
        "*.rs": "Rust",
        "Cargo.toml": "Rust",
        "*.go": "Go",
        "go.mod": "Go",
        "*.rb": "Ruby",
        "Gemfile": "Ruby",
        "*.php": "PHP",
        "composer.json": "PHP",
        "*.cs": "C#",
        "*.csproj": "C#",
        "*.sln": "C#",
        "*.swift": "Swift",
        "Package.swift": "Swift",
        "*.kt": "Kotlin",
        "Dockerfile": "Docker",
    }

    def scan(self, path: Path | str) -> ProjectInfo:
        """Scan a project directory and return structured information.

        Args:
            path: Path to the project directory.

        Returns:
            ProjectInfo: Detected project characteristics.
        """
        root = Path(path).expanduser().resolve()
        if not root.exists():
            raise FileNotFoundError(f"Path does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {root}")

        info = ProjectInfo(
            root=root,
            name=root.name,
        )

        # Check Git
        info.has_git = self._check_git(root)

        # Check Docker
        info.has_docker = self._check_docker(root)

        # Detect languages and frameworks
        languages, info.frameworks = self._detect_languages(root)
        info.languages = languages

        # Detect Python specifics
        if "Python" in languages:
            info.python_version = self._detect_python_version(root)
            info.package_manager = self._detect_python_package_manager(root)

        # Detect Node specifics
        if "JavaScript/Node" in languages or "TypeScript" in languages:
            node_info = self._detect_node_info(root)
            info.node_version = node_info.get("version")
            info.package_manager = node_info.get("package_manager", info.package_manager)
            info.scripts = node_info.get("scripts", info.scripts)
            info.dependencies = node_info.get("dependencies", 0)
            info.dev_dependencies = node_info.get("dev_dependencies", 0)

        # Detect Java specifics
        if "Java" in languages:
            info.java_version = self._detect_java_version(root)

        # Detect Rust specifics
        if "Rust" in languages:
            info.rust_toolchain = self._detect_rust_toolchain(root)

        logger.info(
            "Scanned project '%s': languages=%s, git=%s, docker=%s",
            info.name,
            info.languages,
            info.has_git,
            info.has_docker,
        )

        return info

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _check_git(self, root: Path) -> bool:
        """Check if the directory is a Git repository."""
        return (root / ".git").exists()

    def _check_docker(self, root: Path) -> bool:
        """Check if the directory has Docker configuration."""
        if (root / "Dockerfile").exists():
            return True
        if (root / "docker-compose.yml").exists():
            return True
        if (root / "docker-compose.yaml").exists():
            return True
        return False

    def _detect_languages(self, root: Path) -> tuple[list[str], list[str]]:
        """Detect programming languages and frameworks in the project.

        Returns:
            tuple: (list of language names, list of framework names).
        """
        languages: set[str] = set()
        frameworks: list[str] = []

        # Check for indicator files
        for pattern, language in self.LANGUAGE_INDICATORS.items():
            if pattern.startswith("*."):
                # Glob pattern for extensions
                matches = list(root.glob(pattern))
                if matches:
                    languages.add(language)
            else:
                # Exact filename match
                if (root / pattern).exists():
                    languages.add(language)

        # Check package.json for framework detection
        pkg_json = root / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                framework_map = {
                    "react": "React",
                    "vue": "Vue.js",
                    "angular": "Angular",
                    "next": "Next.js",
                    "nuxt": "Nuxt.js",
                    "svelte": "Svelte",
                    "express": "Express.js",
                    "django": "Django",
                    "flask": "Flask",
                    "fastapi": "FastAPI",
                    "spring": "Spring Boot",
                    "tailwindcss": "Tailwind CSS",
                    "bootstrap": "Bootstrap",
                    "jquery": "jQuery",
                    "electron": "Electron",
                    "tensorflow": "TensorFlow",
                    "pytorch": "PyTorch",
                }
                for dep_key, framework in framework_map.items():
                    if any(dep_key in dep.lower() for dep in deps):
                        if framework not in frameworks:
                            frameworks.append(framework)
            except (json.JSONDecodeError, OSError):
                pass

        # Check pyproject.toml for Python framework detection
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            py_frameworks = ["django", "flask", "fastapi", "tornado", "aiohttp", "sqlalchemy"]
            for fw in py_frameworks:
                if fw in content.lower():
                    display_name = fw.title() if fw != "fastapi" else "FastAPI"
                    if display_name not in frameworks:
                        frameworks.append(display_name)

        return sorted(languages), frameworks

    def _detect_python_version(self, root: Path) -> Optional[str]:
        """Detect Python version from .python-version or runtime.txt."""
        python_version_file = root / ".python-version"
        if python_version_file.exists():
            return python_version_file.read_text(encoding="utf-8").strip()

        runtime_txt = root / "runtime.txt"
        if runtime_txt.exists():
            content = runtime_txt.read_text(encoding="utf-8").strip()
            match = re.search(r"python-([\d.]+)", content)
            if match:
                return match.group(1)

        # Check pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            match = re.search(r'requires-python\s*=\s*"[><=!]+\s*([\d.]+)"', pyproject.read_text(encoding="utf-8"))
            if match:
                return match.group(1)

        return None

    def _detect_python_package_manager(self, root: Path) -> str:
        """Detect Python package manager."""
        if (root / "Pipfile").exists():
            return "pipenv"
        if (root / "poetry.lock").exists():
            return "poetry"
        if (root / "pyproject.toml").exists():
            content = root.joinpath("pyproject.toml").read_text(encoding="utf-8")
            if "[tool.poetry]" in content:
                return "poetry"
            if "[tool.uv]" in content:
                return "uv"
            if "[project]" in content:
                return "pip (pyproject.toml)"
        if (root / "requirements.txt").exists():
            return "pip"
        return "unknown"

    def _detect_node_info(self, root: Path) -> dict[str, Any]:
        """Detect Node.js version and package manager info."""
        info: dict[str, Any] = {}

        pkg_json_path = root / "package.json"
        if not pkg_json_path.exists():
            return info

        try:
            data = json.loads(pkg_json_path.read_text(encoding="utf-8"))

            # Node version from engines
            engines = data.get("engines", {})
            info["version"] = engines.get("node")

            # Scripts
            scripts = data.get("scripts", {})
            info["scripts"] = list(scripts.keys())

            # Dependencies
            info["dependencies"] = len(data.get("dependencies", {}))
            info["dev_dependencies"] = len(data.get("devDependencies", {}))
        except (json.JSONDecodeError, OSError):
            pass

        # Detect package manager
        if (root / "pnpm-lock.yaml").exists():
            info["package_manager"] = "pnpm"
        elif (root / "yarn.lock").exists():
            info["package_manager"] = "yarn"
        elif (root / "package-lock.json").exists():
            info["package_manager"] = "npm"
        elif (root / "bun.lockb").exists():
            info["package_manager"] = "bun"

        # .nvmrc for Node version
        nvmrc = root / ".nvmrc"
        if nvmrc.exists() and not info.get("version"):
            info["version"] = nvmrc.read_text(encoding="utf-8").strip()

        return info

    def _detect_java_version(self, root: Path) -> Optional[str]:
        """Detect Java version from pom.xml or build.gradle."""
        pom = root / "pom.xml"
        if pom.exists():
            match = re.search(
                r"<java.version>([\d.]+)</java.version>",
                pom.read_text(encoding="utf-8"),
            )
            if match:
                return match.group(1)

        gradle = root / "build.gradle"
        if gradle.exists():
            match = re.search(
                r"sourceCompatibility\s*=\s*['\"]([\d.]+)['\"]",
                gradle.read_text(encoding="utf-8"),
            )
            if match:
                return match.group(1)

        return None

    def _detect_rust_toolchain(self, root: Path) -> Optional[str]:
        """Detect Rust toolchain from rust-toolchain.toml or rust-toolchain."""
        toolchain_file = root / "rust-toolchain.toml"
        if toolchain_file.exists():
            import yaml
            try:
                data = yaml.safe_load(toolchain_file.read_text(encoding="utf-8"))
                if data and "toolchain" in data:
                    return data["toolchain"].get("channel", str(data["toolchain"]))
            except (yaml.YAMLError, OSError):
                pass

        toolchain_file = root / "rust-toolchain"
        if toolchain_file.exists():
            return toolchain_file.read_text(encoding="utf-8").strip()

        return None
