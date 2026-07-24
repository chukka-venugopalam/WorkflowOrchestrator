"""Unit tests for the WorkspaceManager."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from workflow_orchestrator.core.workspace_manager import (
    WorkspaceManager,
    WorkspaceHandle,
    WorkspaceScope,
)


class TestWorkspaceManager:
    """Test suite for WorkspaceManager."""

    def setup_method(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = WorkspaceManager(
            base_path=self.temp_dir / "workspaces",
            auto_cleanup=False,
        )

    def teardown_method(self) -> None:
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_provision_workspace(self) -> None:
        """Test provisioning a workspace."""
        handle = self.manager.provision()
        assert handle.workspace_id != ""
        assert handle.root_path.exists()
        assert handle.is_active

    def test_provision_with_scope(self) -> None:
        """Test provisioning with a scope."""
        scope = WorkspaceScope(
            allowed_tools=["terminal", "git"],
            max_storage_mb=100,
        )
        handle = self.manager.provision(scope=scope)
        assert handle.scope.allowed_tools == ["terminal", "git"]
        assert handle.scope.max_storage_mb == 100

    def test_provision_with_source(self) -> None:
        """Test provisioning with a source directory."""
        source_dir = self.temp_dir / "source_project"
        source_dir.mkdir()
        (source_dir / "test.txt").write_text("hello")

        handle = self.manager.provision(source_path=source_dir)
        assert (handle.root_path / "test.txt").exists()
        assert (handle.root_path / "test.txt").read_text() == "hello"

    def test_teardown(self) -> None:
        """Test tearing down a workspace."""
        handle = self.manager.provision()
        assert handle.root_path.exists()

        self.manager.teardown(handle)
        assert not handle.root_path.exists()
        assert not handle.is_active

    def test_teardown_all(self) -> None:
        """Test tearing down all workspaces."""
        handle1 = self.manager.provision()
        handle2 = self.manager.provision()
        assert self.manager.active_count == 2

        count = self.manager.teardown_all()
        assert count == 2
        assert self.manager.active_count == 0

    def test_get_handle(self) -> None:
        """Test getting a workspace handle by ID."""
        handle = self.manager.provision()
        retrieved = self.manager.get_handle(handle.workspace_id)
        assert retrieved is not None
        assert retrieved.workspace_id == handle.workspace_id

    def test_get_missing_handle(self) -> None:
        """Test getting a non-existent handle."""
        assert self.manager.get_handle("nonexistent") is None

    def test_resolve_path(self) -> None:
        """Test resolving a path relative to workspace root."""
        handle = self.manager.provision()
        resolved = self.manager.resolve_path(handle, "subdir/file.txt")
        assert str(resolved).startswith(str(handle.root_path))
        assert resolved.name == "file.txt"

    def test_is_within_scope(self) -> None:
        """Test scope checking."""
        handle = self.manager.provision(scope=WorkspaceScope(
            allowed_directories=[str(self.temp_dir / "allowed")],
        ))

        # Within workspace root
        assert self.manager.is_within_scope(handle, handle.root_path / "test.txt")

        # Within explicitly allowed directory
        allowed_dir = self.temp_dir / "allowed"
        allowed_dir.mkdir(exist_ok=True)
        assert self.manager.is_within_scope(handle, allowed_dir / "file.txt")

        # Outside scope
        outside_dir = self.temp_dir / "outside"
        outside_dir.mkdir(exist_ok=True)
        assert not self.manager.is_within_scope(handle, outside_dir / "file.txt")

    def test_list_active(self) -> None:
        """Test listing active workspaces."""
        handle1 = self.manager.provision()
        handle2 = self.manager.provision()
        active = self.manager.list_active()
        assert len(active) == 2

    def test_active_count(self) -> None:
        """Test the active_count property."""
        assert self.manager.active_count == 0
        self.manager.provision()
        assert self.manager.active_count == 1

    def test_base_path(self) -> None:
        """Test the base_path property."""
        assert Path(self.manager.base_path).resolve() == (self.temp_dir / "workspaces").resolve()

    def test_double_teardown(self) -> None:
        """Test that double teardown is safe."""
        handle = self.manager.provision()
        self.manager.teardown(handle)
        self.manager.teardown(handle)  # Should not raise
        assert not handle.is_active
