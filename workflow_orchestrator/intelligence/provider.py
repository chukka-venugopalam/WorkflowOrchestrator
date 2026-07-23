"""Abstract provider interface for AI provider adapters.

All AI providers (Claude, ChatGPT, Gemini, etc.) must implement
this interface. The core orchestrator never calls any provider
directly — it only interacts through ``IProvider``.

The Orchestrator never reasons. All intelligence comes from
external providers through this interface.

No provider-specific implementations exist in this module.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from workflow_orchestrator.intelligence.models import (
    AgentManifest,
    Capability,
    CostEstimate,
    ExecutionRequest,
    ExecutionResult,
    ProviderHealth,
    ProviderManifest,
    ProviderStatus,
)


class IProvider(ABC):
    """Abstract interface that all AI providers must implement.

    Responsibilities:
    - Declare capabilities and metadata via ``manifest()``
    - Check health via ``health()``
    - Submit tasks via ``submit()`` and ``stream()``
    - Cancel in-flight tasks via ``cancel()``
    - Estimate costs via ``estimate_cost()``
    - Manage lifecycle via ``initialize()`` and ``shutdown()``

    Usage:
        >>> class ClaudeProvider(IProvider):
        ...     def manifest(self) -> ProviderManifest: ...
        ...     async def submit(self, request: ExecutionRequest) -> ExecutionResult: ...
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider.

        Called once during application startup. Providers should
        establish connections, load credentials, and perform
        any one-time setup here.

        Raises:
            RuntimeError: If initialization fails irrecoverably.
        """
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shut down the provider gracefully.

        Called once during application shutdown. Providers should
        close connections, release resources, and cancel any
        in-flight tasks.
        """
        ...

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    @abstractmethod
    def manifest(self) -> ProviderManifest:
        """Get the provider's declared manifest.

        Returns:
            ProviderManifest with metadata, capabilities, and limits.

        This method must be deterministic and cheap to call.
        It should never make network requests.
        """
        ...

    @abstractmethod
    async def capabilities(self) -> list[Capability]:
        """Get the list of capabilities this provider offers.

        Returns:
            List of Capability objects this provider supports.

        This may reflect runtime state (e.g., degraded mode may
        report fewer capabilities).
        """
        ...

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Check the current health of the provider.

        Returns:
            ProviderHealth with status, latency, error rate.

        This method MAY make a lightweight network request
        (e.g., a ping endpoint). It SHOULD complete within
        a few seconds.
        """
        ...

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @abstractmethod
    async def submit(self, request: ExecutionRequest) -> ExecutionResult:
        """Submit a task for execution and wait for completion.

        Args:
            request: The execution request with goal, context, etc.

        Returns:
            ExecutionResult with output, artifacts, and status.

        Raises:
            TimeoutError: If execution exceeds ``request.timeout_seconds``.
            ExecutionError: If the provider returns an error.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        request: ExecutionRequest,
    ) -> AsyncIterator[ExecutionResult]:
        """Submit a task and stream partial results.

        Args:
            request: The execution request.

        Yields:
            Partial ExecutionResult objects as they become available.
            The final yielded result has ``success=True`` on completion.

        Raises:
            TimeoutError: If execution exceeds ``request.timeout_seconds``.
        """
        ...
        yield  # pragma: no cover

    @abstractmethod
    async def cancel(self, task_id: str) -> None:
        """Cancel an in-flight task.

        Args:
            task_id: The task identifier to cancel.

        Raises:
            ValueError: If the task is not found or already completed.
        """
        ...

    @abstractmethod
    async def status(self, task_id: str) -> ExecutionResult:
        """Check the status of a submitted task.

        Args:
            task_id: The task identifier.

        Returns:
            ExecutionResult with current status (may be partial).

        Raises:
            ValueError: If the task is not found.
        """
        ...

    # ------------------------------------------------------------------
        # Estimation
    # ------------------------------------------------------------------

    @abstractmethod
    async def estimate_cost(self, request: ExecutionRequest) -> CostEstimate:
        """Estimate the cost of executing a request.

        Args:
            request: The execution request to estimate.

        Returns:
            CostEstimate with estimated cost and confidence.
        """
        ...

    @abstractmethod
    async def estimate_latency(self, request: ExecutionRequest) -> float:
        """Estimate the latency of executing a request in milliseconds.

        Args:
            request: The execution request to estimate.

        Returns:
            Estimated latency in milliseconds.
        """
        ...

    # ------------------------------------------------------------------
    # Support checks
    # ------------------------------------------------------------------

    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses.

        Returns:
            True if ``stream()`` is implemented efficiently.
            Defaults to False.
        """
        return False

    @property
    def provider_id(self) -> str:
        """Shortcut to ``self.manifest().id``."""
        return self.manifest().id

    @property
    def provider_name(self) -> str:
        """Shortcut to ``self.manifest().name``."""
        return self.manifest().name
