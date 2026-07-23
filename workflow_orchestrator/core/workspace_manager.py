"""Workspace manager for sandboxed workspace provisioning.

Manages creation, scoping, cleanup, and lifecycle of workspaces
used by agent tasks.  Each workspace is an isolated directory
with explicit file/tool permissions.

Rules:
- Each agent task gets an isolated workspace (subset or clone)
- Workspace scope is declared upfront
- Writing outside scope is hard-denied
- Workspace is torn down after task completion
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceScope:
    """Declared scope of a workspace.

    Attributes:
        allowed_directories: List of absolute paths the workspace may access.
        allowed_tools: List of tool names the workspace may use.
        max_storage_mb: Maximum storage in MB (0 = unlimited).
        read_only: Whether the workspace is read-only.
    """

    allowed_directories: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    max_storage_mb: int = 0
    read_only: bool = False


@dataclass
class WorkspaceHandle:
    """Handle to a provisioned workspace.

    Attributes:
        workspace_id: Unique workspace identifier.
        root_path: Absolute path to the workspace root directory.
        scope: The declared scope of the workspace.
        created_at: ISO-8601 timestamp of creation.
        is_active: Whether the workspace is still active.
    """

    workspace_id: str
    root_path: Path
    scope: WorkspaceScope = field(default_factory=WorkspaceScope)
    created_at: str = ""
    is_active: bool = True


class WorkspaceManager:
    """Provisions and manages isolated workspaces.

    Usage:
        >>> manager = WorkspaceManager(base_path=Path("/tmp/workspaces"))
        >>> handle = manager.provision(scope=WorkspaceScope(allowed_tools=["git", "terminal"]))
        >>> # ... use workspace at handle.root_path ...
        >>> manager.teardown(handle)
    """

    def __init__(
        self,
        base_path: Path | str | None = None,
        auto_cleanup: bool = True,
    ) -> None:
        """Initialize the workspace manager.

        Args:
            base_path: Root directory for workspace storage. If None,
                uses a system temporary directory.
            auto_cleanup: Whether to clean up orphaned workspaces on init.
        """
        if base_path is None:
            base_path = Path(tempfile.gettempdir()) / "workflow_orchestrator" / "workspaces"
        self._base_path = Path(base_path).expanduser().resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)

        self._active_workspaces: dict[str, WorkspaceHandle] = {}

        if auto_cleanup:
            self._cleanup_orphaned()

    def _cleanup_orphaned(self) -> None:
        """Clean up workspaces that may have been left behind."""
        if not self._base_path.exists():
            return
        for child in self._base_path.iterdir():
            if child.is_dir() and len(child.name) >= 8:
                try:
                    shutil.rmtree(child)
                    logger.debug("Cleaned up orphaned workspace: %s", child)
                except OSError:
                    pass

    @property
    def base_path(self) -> Path:
        """The base directory for all workspaces."""
        return self._base_path

    def provision(
        self,
        scope: WorkspaceScope | None = None,
        source_path: Path | str | None = None,
        workspace_id: str | None = None,
    ) -> WorkspaceHandle:
        """Provision a new workspace.

        Args:
            scope: The declared scope. Uses default if not provided.
            source_path: Optional source directory to copy into the workspace.
            workspace_id: Optional explicit workspace ID.

        Returns:
            A WorkspaceHandle for the provisioned workspace.
        """
        wid = workspace_id or uuid.uuid4().hex[:12]
        workspace_root = self._base_path / wid
        workspace_root.mkdir(parents=True, exist_ok=True)

        if source_path:
            source = Path(source_path).expanduser().resolve()
            if source.exists():
                if source.is_dir():
                    shutil.copytree(source, workspace_root, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, workspace_root)

        import datetime
        handle = WorkspaceHandle(
            workspace_id=wid,
            root_path=workspace_root,
            scope=scope or WorkspaceScope(),
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            is_active=True,
        )

        self._active_workspaces[wid] = handle
        logger.info("Provisioned workspace '%s' at %s", wid, workspace_root)
        return handle

    def teardown(self, handle: WorkspaceHandle) -> None:
        """Tear down a workspace and remove its files.

        Args:
            handle: The workspace handle to teardown.
        """
        if not handle.is_active:
            logger.debug("Workspace '%s' already torn down", handle.workspace_id)
            return

        handle.is_active = False
        self._active_workspaces.pop(handle.workspace_id, None)

        if handle.root_path.exists():
            try:
                shutil.rmtree(handle.root_path)
                logger.debug("Removed workspace '%s' at %s", handle.workspace_id, handle.root_path)
            except OSError as exc:
                logger.warning("Failed to remove workspace '%s': %s", handle.workspace_id, exc)

    def teardown_all(self) -> int:
        """Tear down all active workspaces.

        Returns:
            Number of workspaces torn down.
        """
        count = len(self._active_workspaces)
        for handle in list(self._active_workspaces.values()):
            self.teardown(handle)
        return count

    def get_handle(self, workspace_id: str) -> Optional[WorkspaceHandle]:
        """Get a workspace handle by ID.

        Args:
            workspace_id: The workspace identifier.

        Returns:
            The handle, or None if not found.
        """
        return self._active_workspaces.get(workspace_id)

    def resolve_path(self, handle: WorkspaceHandle, relative_path: str) -> Path:
        """Resolve a path relative to the workspace root.

        Args:
            handle: The workspace handle.
            relative_path: Path relative to workspace root.

        Returns:
            The resolved absolute path.
        """
        return (handle.root_path / relative_path).resolve()

    def is_within_scope(self, handle: WorkspaceHandle, path: Path) -> bool:
        """Check if a path is within the workspace scope.

        Args:
            handle: The workspace handle.
            path: The path to check.

        Returns:
            True if the path is allowed.
        """
        resolved = path.resolve()

        # Always allow paths within the workspace root
        if str(resolved).startswith(str(handle.root_path)):
            return True

        # Check explicitly allowed directories
        for allowed in handle.scope.allowed_directories:
            if str(resolved).startswith(str(Path(allowed).resolve())):
                return True

        return False

    @property
    def active_count(self) -> int:
        """Number of currently active workspaces."""
        return len(self._active_workspaces)

    def list_active(self) -> list[WorkspaceHandle]:
        """List all active workspaces.

        Returns:
            List of active workspace handles.
        """
        return list(self._active_workspaces.values())
