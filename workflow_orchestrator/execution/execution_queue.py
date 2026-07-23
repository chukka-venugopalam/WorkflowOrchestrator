"""Execution queue for scheduling workflow steps.

Implements:
- FIFO queue (default, first-in-first-out)
- Priority queue (sorted by priority score)
- Delayed queue (steps scheduled for future execution)
- Future parallel execution support

The queue is the scheduling backbone — it manages what runs next.
"""

from __future__ import annotations

import heapq
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueueItem:
    """An item in the execution queue.

    Attributes:
        priority: Priority score (lower = higher priority).
        enqueued_at: Timestamp when the item was enqueued.
        node_id: The execution node ID.
        batch_id: The batch this item belongs to.
        metadata: Additional metadata.
    """

    priority: int
    enqueued_at: float
    node_id: str = ""
    batch_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)


@dataclass
class DelayedItem:
    """An item scheduled for future execution.

    Attributes:
        execute_at: Unix timestamp when this item should execute.
        node_id: The execution node ID.
        batch_id: The batch this item belongs to.
        priority: Priority after delay expires.
    """

    execute_at: float
    node_id: str
    batch_id: str = ""
    priority: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionQueue:
    """Queue for scheduling and managing workflow step execution.

    Supports:
    - FIFO ordering (default)
    - Priority-based ordering
    - Delayed execution (scheduled for future)
    - Batch operations

    Usage:
        >>> queue = ExecutionQueue()
        >>> queue.enqueue("step_1", batch_id="batch_1")
        >>> queue.enqueue("step_2", priority=50)  # Higher priority
        >>> item = queue.dequeue()
        >>> print(item.node_id)
        'step_2'
    """

    def __init__(self) -> None:
        self._fifo: list[QueueItem] = []
        self._priority: list[QueueItem] = []  # heapq
        self._delayed: list[DelayedItem] = []
        self._enqueued_count: int = 0
        self._dequeued_count: int = 0

    # ------------------------------------------------------------------
    # Enqueue
    # ------------------------------------------------------------------

    def enqueue(
        self,
        node_id: str,
        batch_id: str = "",
        priority: int = 100,
        delay_seconds: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Enqueue a step for execution.

        Args:
            node_id: The execution node ID.
            batch_id: Optional batch identifier.
            priority: Priority (lower = higher priority, default 100).
            delay_seconds: Delay before execution in seconds.
            metadata: Additional metadata.
        """
        now = time.time()

        if delay_seconds > 0:
            # Delayed execution
            delayed = DelayedItem(
                execute_at=now + delay_seconds,
                node_id=node_id,
                batch_id=batch_id,
                priority=priority,
                metadata=metadata or {},
            )
            self._delayed.append(delayed)
            logger.debug("Delayed enqueue '%s' for %.1fs", node_id, delay_seconds)
        else:
            # Immediate enqueue to both FIFO and priority queue
            item = QueueItem(
                priority=priority,
                enqueued_at=now,
                node_id=node_id,
                batch_id=batch_id,
                metadata=metadata or {},
            )
            self._fifo.append(item)
            heapq.heappush(self._priority, item)

        self._enqueued_count += 1

    def enqueue_batch(
        self,
        node_ids: list[str],
        batch_id: str = "",
        priority: int = 100,
    ) -> None:
        """Enqueue multiple steps in a single batch.

        Args:
            node_ids: List of execution node IDs.
            batch_id: Optional batch identifier.
            priority: Priority for all steps in the batch.
        """
        for nid in node_ids:
            self.enqueue(nid, batch_id=batch_id, priority=priority)

    # ------------------------------------------------------------------
    # Dequeue
    # ------------------------------------------------------------------

    def dequeue(
        self,
        mode: str = "priority",
    ) -> QueueItem | None:
        """Dequeue the next ready step.

        Args:
            mode: Dequeue mode (``priority``, ``fifo``).

        Returns:
            The next QueueItem, or None if queue is empty.

        Note:
            Delayed items are automatically promoted to the main queue
            when their execution time arrives.
        """
        # Process delayed items that are ready
        self._promote_delayed()

        if mode == "fifo":
            if not self._fifo:
                return None
            item = self._fifo.pop(0)
            self._dequeued_count += 1
            return item

        # Default: priority mode
        if not self._priority:
            return None
        item = heapq.heappop(self._priority)
        self._dequeued_count += 1
        return item

    def dequeue_batch(
        self,
        max_items: int = 10,
        mode: str = "priority",
    ) -> list[QueueItem]:
        """Dequeue multiple items at once.

        Args:
            max_items: Maximum items to dequeue.
            mode: Dequeue mode.

        Returns:
            List of dequeued items.
        """
        items: list[QueueItem] = []
        for _ in range(max_items):
            item = self.dequeue(mode=mode)
            if item is None:
                break
            items.append(item)
        return items

    def _promote_delayed(self) -> None:
        """Promote delayed items whose execution time has arrived."""
        now = time.time()
        ready: list[DelayedItem] = []

        # Find all delayed items that are ready
        remaining: list[DelayedItem] = []
        for item in self._delayed:
            if item.execute_at <= now:
                ready.append(item)
            else:
                remaining.append(item)

        self._delayed = remaining

        # Promote to main queue
        for item in ready:
            logger.debug("Promoting delayed item '%s' to main queue", item.node_id)
            self.enqueue(
                node_id=item.node_id,
                batch_id=item.batch_id,
                priority=item.priority,
                metadata=item.metadata,
            )

    # ------------------------------------------------------------------
    # Queue state
    # ------------------------------------------------------------------

    def peek(self, mode: str = "priority") -> QueueItem | None:
        """Peek at the next item without dequeuing.

        Args:
            mode: Peek mode (``priority`` or ``fifo``).

        Returns:
            The next item or None.
        """
        self._promote_delayed()

        if mode == "fifo":
            return self._fifo[0] if self._fifo else None

        return self._priority[0] if self._priority else None

    def clear(self) -> None:
        """Clear all items from the queue."""
        self._fifo.clear()
        self._priority.clear()
        self._delayed.clear()

    @property
    def size(self) -> int:
        """Total number of items in the queue."""
        self._promote_delayed()
        return max(len(self._fifo), len(self._priority)) + len(self._delayed)

    @property
    def is_empty(self) -> bool:
        """Whether the queue is empty."""
        return self.size == 0

    @property
    def enqueued_count(self) -> int:
        """Total number of items enqueued."""
        return self._enqueued_count

    @property
    def dequeued_count(self) -> int:
        """Total number of items dequeued."""
        return self._dequeued_count

    def get_delayed_count(self) -> int:
        """Number of delayed items waiting."""
        return len(self._delayed)
