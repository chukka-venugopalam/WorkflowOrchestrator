"""Step executor — executes a single workflow step via plugin dispatch.

Responsible only for executing one step at a time.
No planning, no routing, no scheduling — pure execution.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from workflow_orchestrator.execution.execution_context import ExecutionContext
from workflow_orchestrator.execution.workflow_compiler import ExecutionNode
from workflow_orchestrator.models import StepResult, StepStatus

logger = logging.getLogger(__name__)


class StepExecutor:
    """Executes a single workflow step by dispatching to the appropriate plugin.

    The StepExecutor is the innermost execution primitive — it takes one node,
    finds the matching plugin, runs it, and returns the result. It knows
    nothing about workflows, dependencies, or scheduling.

    Usage:
        >>> executor = StepExecutor()
        >>> context = ExecutionContext.create(workflow_name="test")
        >>> result = executor.execute(node, context)
        >>> print(result.status)
        StepStatus.SUCCESS
    """

    def __init__(self, plugin_registry: Any = None) -> None:
        """Initialize the step executor.

        Args:
            plugin_registry: Optional plugin registry for resolving plugins.
                If None, plugins are resolved via the global registry.
        """
        self._plugin_registry = plugin_registry

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        node: ExecutionNode,
        context: ExecutionContext,
        dry_run: bool = False,
    ) -> StepResult:
        """Execute a single step node.

        Args:
            node: The execution node to execute.
            context: The current execution context.
            dry_run: If True, simulate execution without actually running.

        Returns:
            A StepResult with the execution outcome.
        """
        start_time = time.time()
        step_name = node.name or f"{node.plugin}:{node.step_index}"

        logger.info(
            "Executing step '%s' (plugin: %s, node: %s)",
            step_name,
            node.plugin,
            node.node_id,
        )

        if dry_run:
            time.sleep(0.1)  # Simulate minimal work
            return StepResult(
                step_name=step_name,
                plugin=node.plugin,
                status=StepStatus.SUCCESS,
                duration=time.time() - start_time,
                message=f"Dry-run: {step_name} completed (simulated)",
                output={"dry_run": True, "node_id": node.node_id},
            )

        # Dispatch to plugin
        try:
            plugin = self._resolve_plugin(node.plugin)
        except ValueError as exc:
            duration = time.time() - start_time
            logger.error("Plugin resolution failed for '%s': %s", node.plugin, exc)
            return StepResult(
                step_name=step_name,
                plugin=node.plugin,
                status=StepStatus.FAILURE,
                duration=duration,
                message=str(exc),
                error=str(exc),
            )

        # Execute the plugin
        try:
            plugin_result = self._run_plugin(plugin, node, context)
            duration = time.time() - start_time

            if plugin_result.get("success", True):
                status = StepStatus.SUCCESS
                message = plugin_result.get("message", f"Step '{step_name}' completed")
            else:
                status = StepStatus.FAILURE
                message = plugin_result.get("message", f"Step '{step_name}' failed")

            result = StepResult(
                step_name=step_name,
                plugin=node.plugin,
                status=status,
                duration=duration,
                message=message,
                output=plugin_result.get("output", {}),
                error=plugin_result.get("error"),
                attempts=1,
            )

            # Record output in context
            if status == StepStatus.SUCCESS:
                context.record_output(node.node_id, result.output)

            logger.debug(
                "Step '%s' completed: %s (%.2fs)",
                step_name,
                status.value,
                duration,
            )
            return result

        except Exception as exc:
            duration = time.time() - start_time
            logger.exception("Step '%s' raised exception: %s", step_name, exc)
            return StepResult(
                step_name=step_name,
                plugin=node.plugin,
                status=StepStatus.FAILURE,
                duration=duration,
                message="Unexpected execution error",
                output={},
                error=str(exc),
                attempts=1,
            )

    # ------------------------------------------------------------------
    # Plugin resolution
    # ------------------------------------------------------------------

    def _resolve_plugin(self, plugin_name: str) -> Any:
        """Resolve a plugin by name.

        Args:
            plugin_name: Name of the plugin to resolve.

        Returns:
            The plugin instance.

        Raises:
            ValueError: If the plugin cannot be resolved.
        """
        # Try the injected registry first
        if self._plugin_registry is not None:
            try:
                return self._plugin_registry.get_plugin(plugin_name)
            except (KeyError, AttributeError):
                pass

        # Fall back to the global plugin registry
        try:
            from workflow_orchestrator.plugins.registry import default_registry
            return default_registry.get(plugin_name)
        except (KeyError, AttributeError, ImportError):
            pass

        # Try direct import of plugin module
        try:
            import importlib
            module_path = f"workflow_orchestrator.plugins.{plugin_name}_plugin"
            module = importlib.import_module(module_path)
            # Look for a class or function matching the plugin name
            for attr_name in dir(module):
                if plugin_name.replace("_", "").lower() in attr_name.lower():
                    attr = getattr(module, attr_name)
                    if callable(attr):
                        return attr
            return module
        except (ImportError, AttributeError):
            pass

        raise ValueError(
            f"Plugin '{plugin_name}' not found. "
            "Ensure the plugin is registered in the plugin registry."
        )

    def _run_plugin(
        self,
        plugin: Any,
        node: ExecutionNode,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Run a plugin against a node and context.

        Args:
            plugin: The resolved plugin instance or callable.
            node: The execution node.
            context: The execution context.

        Returns:
            Dict with keys: success, message, output, error.
        """
        # Extract config from the node
        config = dict(node.config)

        # Merge context variables into config for plugin access
        config.setdefault("context", {})
        if isinstance(config["context"], dict):
            config["context"].update({
                "execution_id": context.execution_id,
                "workflow_id": context.workflow_id,
                "step_name": node.name,
                "variables": dict(context.variables),
            })

        # Try different invocation patterns
        # Pattern 1: plugin.execute(config)
        if hasattr(plugin, "execute") and callable(getattr(plugin, "execute")):
            result = plugin.execute(config)
            if isinstance(result, dict):
                return result
            return {"success": True, "output": {"result": str(result)}}

        # Pattern 2: plugin(config) — callable
        if callable(plugin):
            result = plugin(config)
            if isinstance(result, dict):
                return result
            return {"success": True, "output": {"result": str(result)}}

        # Pattern 3: plugin.run(config) or plugin.handle(config)
        for method_name in ("run", "handle", "invoke"):
            if hasattr(plugin, method_name) and callable(getattr(plugin, method_name)):
                method = getattr(plugin, method_name)
                result = method(config)
                if isinstance(result, dict):
                    return result
                return {"success": True, "output": {"result": str(result)}}

        return {
            "success": False,
            "error": f"Plugin '{node.plugin}' has no callable entry point",
            "message": f"Plugin '{node.plugin}' is not executable",
        }
