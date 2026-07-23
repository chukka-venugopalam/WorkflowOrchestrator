"""Unit tests for ExecutionQueue."""

from __future__ import annotations

import time

from workflow_orchestrator.execution.execution_queue import ExecutionQueue


class TestExecutionQueue:
    """Tests for the ExecutionQueue."""

    def setup_method(self) -> None:
        self.queue = ExecutionQueue()

    def test_enqueue_dequeue_fifo(self) -> None:
        """Test FIFO enqueue/dequeue."""
        self.queue.enqueue("step_1")
        self.queue.enqueue("step_2")
        self.queue.enqueue("step_3")

        item1 = self.queue.dequeue(mode="fifo")
        item2 = self.queue.dequeue(mode="fifo")
        item3 = self.queue.dequeue(mode="fifo")

        assert item1 is not None
        assert item1.node_id == "step_1"
        assert item2 is not None
        assert item2.node_id == "step_2"
        assert item3 is not None
        assert item3.node_id == "step_3"

    def test_enqueue_dequeue_priority(self) -> None:
        """Test priority enqueue/dequeue (lower number = higher priority)."""
        self.queue.enqueue("step_low", priority=100)
        self.queue.enqueue("step_high", priority=10)
        self.queue.enqueue("step_medium", priority=50)

        item1 = self.queue.dequeue()
        item2 = self.queue.dequeue()
        item3 = self.queue.dequeue()

        assert item1.node_id == "step_high"
        assert item2.node_id == "step_medium"
        assert item3.node_id == "step_low"

    def test_delayed_execution(self) -> None:
        """Test that delayed items are not immediately available."""
        self.queue.enqueue("step_immediate")
        self.queue.enqueue("step_delayed", delay_seconds=10.0)

        item = self.queue.dequeue()
        assert item is not None
        assert item.node_id == "step_immediate"

        # Delayed should not be available yet
        item2 = self.queue.dequeue()
        assert item2 is None

    def test_delayed_becomes_available(self) -> None:
        """Test that delayed items become available after their delay."""
        self.queue.enqueue("step_delayed", delay_seconds=0.01)
        time.sleep(0.05)

        # The delayed item should now be promoted
        item = self.queue.dequeue()
        assert item is not None
        assert item.node_id == "step_delayed"

    def test_dequeue_empty(self) -> None:
        """Test dequeuing from an empty queue."""
        item = self.queue.dequeue()
        assert item is None

    def test_peek(self) -> None:
        """Test peeking without removing."""
        self.queue.enqueue("step_1", priority=50)
        self.queue.enqueue("step_2", priority=10)

        peeked = self.queue.peek()
        assert peeked is not None
        assert peeked.node_id == "step_2"

        # Peek should not remove the item
        assert self.queue.size == 2

    def test_clear(self) -> None:
        """Test clearing the queue."""
        self.queue.enqueue("step_1")
        self.queue.enqueue("step_2")
        assert self.queue.size == 2

        self.queue.clear()
        assert self.queue.is_empty
        assert self.queue.size == 0

    def test_enqueue_batch(self) -> None:
        """Test batch enqueue."""
        self.queue.enqueue_batch(["step_1", "step_2", "step_3"], batch_id="batch_1")
        assert self.queue.size == 3
        assert self.queue.enqueued_count == 3

    def test_dequeue_batch(self) -> None:
        """Test batch dequeue."""
        self.queue.enqueue_batch(
            ["step_1", "step_2", "step_3", "step_4", "step_5"],
            batch_id="batch_1",
        )
        items = self.queue.dequeue_batch(max_items=3)
        assert len(items) == 3
        # Remaining items should still be in the queue
        assert not self.queue.is_empty

    def test_size_and_empty_properties(self) -> None:
        """Test size and is_empty properties."""
        assert self.queue.is_empty
        assert self.queue.size == 0

        self.queue.enqueue("step_1")
        assert not self.queue.is_empty
        assert self.queue.size == 1

    def test_counters(self) -> None:
        """Test enqueued and dequeued counters."""
        self.queue.enqueue("step_1")
        self.queue.enqueue("step_2")
        self.queue.dequeue()
        assert self.queue.enqueued_count == 2
        assert self.queue.dequeued_count == 1

    def test_get_delayed_count(self) -> None:
        """Test get_delayed_count."""
        assert self.queue.get_delayed_count() == 0
        self.queue.enqueue("step_delayed", delay_seconds=60.0)
        assert self.queue.get_delayed_count() == 1
