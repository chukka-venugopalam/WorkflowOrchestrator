"""Unit tests for the LifecycleManager."""

from __future__ import annotations

from workflow_orchestrator.core.lifecycle import (
    LifecycleManager,
    HookPriority,
    LifecycleHook,
)


class TestLifecycleManager:
    """Test suite for LifecycleManager."""

    def setup_method(self) -> None:
        self.lifecycle = LifecycleManager()
        self.execution_order: list[str] = []

    def _make_handler(self, name: str) -> callable:
        def handler():
            self.execution_order.append(name)
            return True
        return handler

    def test_register_startup_hook(self) -> None:
        """Test registering a startup hook."""
        hook = self.lifecycle.on_startup("test", lambda: True)
        assert hook.name == "test"
        assert self.lifecycle.startup_count == 1

    def test_register_shutdown_hook(self) -> None:
        """Test registering a shutdown hook."""
        hook = self.lifecycle.on_shutdown("test", lambda: True)
        assert hook.name == "test"
        assert self.lifecycle.shutdown_count == 1

    def test_run_startup_all_success(self) -> None:
        """Test running all startup hooks successfully."""
        self.lifecycle.on_startup("hook1", self._make_handler("hook1"))
        self.lifecycle.on_startup("hook2", self._make_handler("hook2"))
        assert self.lifecycle.run_startup()
        assert self.execution_order == ["hook1", "hook2"]

    def test_run_startup_priority_order(self) -> None:
        """Test that hooks run in priority order."""
        self.lifecycle.on_startup(
            "low", self._make_handler("low"), priority=HookPriority.LOW,
        )
        self.lifecycle.on_startup(
            "critical", self._make_handler("critical"), priority=HookPriority.CRITICAL,
        )
        self.lifecycle.on_startup(
            "normal", self._make_handler("normal"), priority=HookPriority.NORMAL,
        )
        self.lifecycle.run_startup()
        assert self.execution_order == ["critical", "normal", "low"]

    def test_run_startup_with_failure(self) -> None:
        """Test that a hook failure doesn't stop other hooks."""
        def failing():
            raise ValueError("Failure")

        self.lifecycle.on_startup("fail", failing)
        self.lifecycle.on_startup("ok", self._make_handler("ok"))

        result = self.lifecycle.run_startup()
        assert not result  # Overall failure
        assert self.execution_order == ["ok"]  # 'ok' still runs

    def test_run_shutdown_reverse_priority(self) -> None:
        """Test that shutdown hooks run in reverse priority."""
        self.lifecycle.on_shutdown(
            "critical", self._make_handler("critical"), priority=HookPriority.CRITICAL,
        )
        self.lifecycle.on_shutdown(
            "normal", self._make_handler("normal"), priority=HookPriority.NORMAL,
        )
        self.lifecycle.on_shutdown(
            "low", self._make_handler("low"), priority=HookPriority.LOW,
        )
        self.lifecycle.run_shutdown()
        # Shutdown runs in reverse priority order
        assert self.execution_order == ["low", "normal", "critical"]

    def test_list_startup_hooks(self) -> None:
        """Test listing startup hooks in priority order."""
        self.lifecycle.on_startup("b", lambda: True)
        self.lifecycle.on_startup("a", lambda: True)
        hooks = self.lifecycle.list_startup_hooks()
        assert len(hooks) == 2
        assert hooks[0].name in ("a", "b")

    def test_list_shutdown_hooks(self) -> None:
        """Test listing shutdown hooks."""
        self.lifecycle.on_shutdown("test", lambda: True)
        hooks = self.lifecycle.list_shutdown_hooks()
        assert len(hooks) == 1
        assert hooks[0].name == "test"

    def test_clear(self) -> None:
        """Test clearing all hooks."""
        self.lifecycle.on_startup("a", lambda: True)
        self.lifecycle.on_shutdown("b", lambda: True)
        self.lifecycle.clear()
        assert self.lifecycle.startup_count == 0
        assert self.lifecycle.shutdown_count == 0
