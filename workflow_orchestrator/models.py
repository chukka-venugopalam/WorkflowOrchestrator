"""Shared data models for the Workflow Orchestrator.

Defines dataclasses used across the engine, plugins, scheduler,
reports, and CLI layers. All models use Python 3.12+ type hints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Optional

import yaml


# ---------------------------------------------------------------------------
# Step result
# ---------------------------------------------------------------------------


class StepStatus(Enum):
    """Status of a workflow step execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class StepResult:
    """Result of executing a single workflow step.

    Attributes:
        step_name: Human-readable name of the step.
        plugin: Name of the plugin that executed the step.
        status: Execution status.
        duration: Execution duration in seconds.
        message: Human-readable result message.
        output: Arbitrary output data from the step.
        error: Error details if the step failed.
        attempts: Number of attempts made (for retries).
    """

    step_name: str
    plugin: str
    status: StepStatus = StepStatus.PENDING
    duration: float = 0.0
    message: str = ""
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "step_name": self.step_name,
            "plugin": self.plugin,
            "status": self.status.value,
            "duration": round(self.duration, 3),
            "message": self.message,
            "output": self.output,
            "error": self.error,
            "attempts": self.attempts,
        }


# ---------------------------------------------------------------------------
# Retry / error recovery
# ---------------------------------------------------------------------------


@dataclass
class RetryConfig:
    """Configuration for retrying a failed step.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retry).
        delay: Delay in seconds between retries.
        backoff: Multiplier for exponential backoff (1.0 = fixed delay).
    """

    max_retries: int = 0
    delay: float = 1.0
    backoff: float = 1.0


class OnFailure(Enum):
    """Action to take when a workflow step fails."""

    STOP = "stop"
    CONTINUE = "continue"
    RETRY = "retry"


# ---------------------------------------------------------------------------
# Workflow definition (loaded from YAML)
# ---------------------------------------------------------------------------


@dataclass
class WorkflowStep:
    """A single step in a workflow definition.

    Attributes:
        name: Optional human-readable name (auto-generated if empty).
        plugin: Plugin identifier (e.g., 'terminal', 'browser').
        config: Plugin-specific configuration dictionary.
        on_failure: Action on failure (stop, continue, retry).
        retry: Retry configuration.
    """

    name: str = ""
    plugin: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    on_failure: OnFailure = OnFailure.STOP
    retry: RetryConfig = field(default_factory=RetryConfig)

    # Step key aliases: maps user-friendly short-form keys to actual plugin names
    # and optionally injects default config values.
    STEP_ALIASES: ClassVar[dict[str, tuple[str, dict[str, Any]]]] = {
        "open_url": ("browser", {"action": "open_url"}),
        "open_github": ("browser", {"action": "open_github"}),
        "open_render": ("browser", {"action": "open_render"}),
        "open_vercel": ("browser", {"action": "open_vercel"}),
        "open_app": ("open_app", {}),
    }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowStep:
        """Create a step from a parsed YAML dictionary.

        The YAML format supports both short and long forms:
        ```yaml
        - terminal:
            command: git status
        ```
        or
        ```yaml
        - name: Check Git status
          plugin: terminal
          config:
            command: git status
        ```

        Short-form keys like ``open_url`` and ``open_app`` are automatically
        mapped to their corresponding plugins (``browser``, ``open_app``).
        """
        # Short form: single key with config as value
        if len(data) == 1:
            raw_plugin_name = next(iter(data))
            config_value = data[raw_plugin_name]

            # Resolve step aliases
            if raw_plugin_name in cls.STEP_ALIASES:
                actual_plugin, default_config = cls.STEP_ALIASES[raw_plugin_name]
                merged_config = {**default_config}
                if isinstance(config_value, dict):
                    merged_config.update(config_value)
                step_name = merged_config.get("url", config_value.get("app", raw_plugin_name)) if isinstance(config_value, dict) else raw_plugin_name
                return cls(
                    name=f"{raw_plugin_name}: {step_name}",
                    plugin=actual_plugin,
                    config=merged_config,
                )

            if isinstance(config_value, dict):
                return cls(
                    name=f"{raw_plugin_name}: {config_value.get('command', config_value.get('url', config_value.get('app', '')))}",
                    plugin=raw_plugin_name,
                    config=config_value,
                )
            return cls(name=raw_plugin_name, plugin=raw_plugin_name, config={"value": config_value})

        # Long form
        name = data.get("name", "")
        plugin = data.get("plugin", "")
        config = data.get("config", data.get("params", {}))
        raw_on_failure = data.get("on_failure", "stop")
        raw_retry = data.get("retry", {})

        try:
            on_failure = OnFailure(raw_on_failure)
        except ValueError:
            on_failure = OnFailure.STOP

        if isinstance(raw_retry, dict):
            retry = RetryConfig(
                max_retries=raw_retry.get("max_retries", 0),
                delay=raw_retry.get("delay", 1.0),
                backoff=raw_retry.get("backoff", 1.0),
            )
        elif isinstance(raw_retry, int):
            retry = RetryConfig(max_retries=raw_retry)
        else:
            retry = RetryConfig()

        return cls(
            name=name,
            plugin=plugin,
            config=config,
            on_failure=on_failure,
            retry=retry,
        )


@dataclass
class WorkflowDefinition:
    """A complete workflow loaded from a YAML file.

    Attributes:
        name: Human-readable workflow name.
        description: Optional description of the workflow.
        steps: Ordered list of steps to execute.
        source: Path to the source YAML file (empty if created programmatically).
        tags: Optional list of tags for categorization.
        schedule: Optional schedule configuration.
    """

    name: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    source: str = ""
    tags: list[str] = field(default_factory=list)
    schedule: Optional[dict[str, Any]] = None

    @classmethod
    def from_yaml(cls, path: Path) -> WorkflowDefinition:
        """Load a workflow definition from a YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            WorkflowDefinition: Parsed workflow.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the YAML content is invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        if not data or "steps" not in data:
            raise ValueError(f"Invalid workflow file: missing 'steps' key in {path}")

        name = data.get("name", path.stem.replace("_", " ").title())
        description = data.get("description", "")
        tags = data.get("tags", [])
        schedule = data.get("schedule")

        raw_steps = data["steps"]
        if not isinstance(raw_steps, list):
            raise ValueError("Workflow 'steps' must be a list")

        steps = [WorkflowStep.from_dict(step) for step in raw_steps]

        return cls(
            name=name,
            description=description,
            steps=steps,
            source=str(path),
            tags=tags,
            schedule=schedule,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "name": s.name,
                    "plugin": s.plugin,
                    "config": s.config,
                    "on_failure": s.on_failure.value,
                    "retry": {
                        "max_retries": s.retry.max_retries,
                        "delay": s.retry.delay,
                        "backoff": s.retry.backoff,
                    },
                }
                for s in self.steps
            ],
            "source": self.source,
            "tags": self.tags,
            "schedule": self.schedule,
        }


# ---------------------------------------------------------------------------
# Execution report
# ---------------------------------------------------------------------------


@dataclass
class ExecutionReport:
    """Record of a complete workflow execution.

    Attributes:
        workflow_name: Name of the workflow that was executed.
        workflow_source: Source file of the workflow.
        timestamp: ISO-8601 timestamp when execution started.
        duration: Total execution duration in seconds.
        steps: Results of each step execution.
        successful_steps: Count of successful steps.
        failed_steps: Count of failed steps.
        total_steps: Total number of steps.
        success: Whether the entire workflow succeeded.
        logs: Captured log entries during execution.
        error: Overall error message if the workflow failed.
        profile: Configuration profile used.
    """

    workflow_name: str
    workflow_source: str = ""
    timestamp: str = ""
    duration: float = 0.0
    steps: list[StepResult] = field(default_factory=list)
    successful_steps: int = 0
    failed_steps: int = 0
    total_steps: int = 0
    success: bool = True
    logs: list[str] = field(default_factory=list)
    error: Optional[str] = None
    profile: str = "default"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "workflow_name": self.workflow_name,
            "workflow_source": self.workflow_source,
            "timestamp": self.timestamp,
            "duration": round(self.duration, 3),
            "steps": [s.to_dict() for s in self.steps],
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "total_steps": self.total_steps,
            "success": self.success,
            "logs": self.logs[-50:],  # Keep last 50 log entries
            "error": self.error,
            "profile": self.profile,
        }


# ---------------------------------------------------------------------------
# Project scanner models
# ---------------------------------------------------------------------------


@dataclass
class ProjectInfo:
    """Structured information about a scanned project.

    Attributes:
        root: Root directory of the project.
        name: Project name (from root directory name).
        languages: Detected programming languages.
        package_manager: Detected package manager.
        has_git: Whether the project is a Git repository.
        has_docker: Whether the project has Docker configuration.
        python_version: Detected Python version (if applicable).
        node_version: Detected Node.js version (if applicable).
        java_version: Detected Java version (if applicable).
        rust_toolchain: Detected Rust toolchain (if applicable).
        frameworks: Detected frameworks/libraries.
        scripts: Available package scripts.
        dependencies: Count of dependencies.
        dev_dependencies: Count of dev dependencies.
    """

    root: Path
    name: str = ""
    languages: list[str] = field(default_factory=list)
    package_manager: Optional[str] = None
    has_git: bool = False
    has_docker: bool = False
    python_version: Optional[str] = None
    node_version: Optional[str] = None
    java_version: Optional[str] = None
    rust_toolchain: Optional[str] = None
    frameworks: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    dependencies: int = 0
    dev_dependencies: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "root": str(self.root),
            "name": self.name,
            "languages": self.languages,
            "package_manager": self.package_manager,
            "has_git": self.has_git,
            "has_docker": self.has_docker,
            "python_version": self.python_version,
            "node_version": self.node_version,
            "java_version": self.java_version,
            "rust_toolchain": self.rust_toolchain,
            "frameworks": self.frameworks,
            "scripts": self.scripts,
            "dependencies": self.dependencies,
            "dev_dependencies": self.dev_dependencies,
        }


# ---------------------------------------------------------------------------
# Profile configuration
# ---------------------------------------------------------------------------


@dataclass
class ProfileConfig:
    """Configuration profile loaded from a YAML file.

    Attributes:
        name: Profile name.
        description: Optional description.
        brave_executable_path: Path to Brave browser.
        vscode_executable_path: Path to VS Code.
        default_project_directory: Default project directory.
        github_repository_url: GitHub repo URL.
        render_dashboard_url: Render dashboard URL.
        vercel_dashboard_url: Vercel dashboard URL.
        freebuff_command: Command to launch Freebuff.
        env: Environment variables to set.
        custom: Additional custom configuration.
    """

    name: str = "default"
    description: str = ""
    brave_executable_path: str = ""
    vscode_executable_path: str = "code"
    default_project_directory: str = ""
    github_repository_url: str = ""
    render_dashboard_url: str = ""
    vercel_dashboard_url: str = ""
    freebuff_command: str = ""
    env: dict[str, str] = field(default_factory=dict)
    custom: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> ProfileConfig:
        """Load a profile from a YAML file.

        Args:
            path: Path to the YAML profile file.

        Returns:
            ProfileConfig: Loaded profile.
        """
        if not path.exists():
            return cls(name=path.stem)

        with open(path, "r", encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        known_keys = {
            "name", "description", "brave_executable_path",
            "vscode_executable_path", "default_project_directory",
            "github_repository_url", "render_dashboard_url",
            "vercel_dashboard_url", "freebuff_command", "env",
        }

        known = {k: v for k, v in data.items() if k in known_keys}
        custom = {k: v for k, v in data.items() if k not in known_keys}

        return cls(**known, custom=custom)

    def to_app_config_dict(self) -> dict[str, Any]:
        """Convert to a flat dictionary compatible with AppConfig."""
        return {
            "brave_executable_path": self.brave_executable_path,
            "vscode_executable_path": self.vscode_executable_path,
            "default_project_directory": self.default_project_directory,
            "github_repository_url": self.github_repository_url,
            "render_dashboard_url": self.render_dashboard_url,
            "vercel_dashboard_url": self.vercel_dashboard_url,
            "freebuff_command": self.freebuff_command,
            **self.custom,
        }
