"""Unit tests for the EventBus (in-process pub/sub)."""

from __future__ import annotations

import pytest

from workflow_orchestrator.core.event_bus import EventBus, Event, Subscription


class TestEventBus:
    """Test suite for EventBus."""

    def setup_method(self) -> None:
        self.bus = EventBus()
        self.received_events: list[Event] = []

    def _handler(self, event: Event) -> None:
        self.received_events.append(event)

    def test_publish_and_subscribe(self) -> None:
        """Test that subscribers receive published events."""
        sub = self.bus.subscribe("test.event", self._handler)
        event = Event(type="test.event", data={"key": "value"})
        self.bus.publish(event)

        assert len(self.received_events) == 1
        assert self.received_events[0].type == "test.event"
        assert self.received_events[0].data == {"key": "value"}

    def test_pattern_matching(self) -> None:
        """Test glob pattern matching for event types."""
        self.bus.subscribe("step.*", self._handler)

        self.bus.publish(Event(type="step.started", data={"step": 1}))
        self.bus.publish(Event(type="step.completed", data={"step": 1}))
        self.bus.publish(Event(type="workflow.done", data={}))

        assert len(self.received_events) == 2
        assert self.received_events[0].type == "step.started"
        assert self.received_events[1].type == "step.completed"

    def test_multiple_subscribers(self) -> None:
        """Test that multiple subscribers receive the same event."""
        received2: list[Event] = []

        self.bus.subscribe("test.*", self._handler)
        self.bus.subscribe("test.*", lambda e: received2.append(e))

        self.bus.publish(Event(type="test.event"))

        assert len(self.received_events) == 1
        assert len(received2) == 1

    def test_unsubscribe(self) -> None:
        """Test that unsubscribed handlers no longer receive events."""
        sub = self.bus.subscribe("test.event", self._handler)
        self.bus.publish(Event(type="test.event"))
        assert len(self.received_events) == 1

        self.bus.unsubscribe(sub)
        self.bus.publish(Event(type="test.event"))
        assert len(self.received_events) == 1  # No new events

    def test_unsubscribe_by_id(self) -> None:
        """Test unsubscribing by subscription ID."""
        sub = self.bus.subscribe("test.event", self._handler)
        self.bus.unsubscribe_by_id(sub.id)
        self.bus.publish(Event(type="test.event"))
        assert len(self.received_events) == 0

    def test_subscriber_isolation(self) -> None:
        """Test that one subscriber exception doesn't affect others."""
        def failing_handler(event: Event) -> None:
            raise ValueError("This handler fails")

        self.bus.subscribe("test.event", failing_handler)
        self.bus.subscribe("test.event", self._handler)

        self.bus.publish(Event(type="test.event"))
        assert len(self.received_events) == 1

    def test_no_matching_subscribers(self) -> None:
        """Test publishing with no matching subscribers."""
        self.bus.publish(Event(type="unmatched.event"))
        # Should not raise any error

    def test_event_auto_fields(self) -> None:
        """Test that events get auto-generated fields."""
        event = Event(type="test.event")
        assert event.type == "test.event"
        assert event.event_id != ""
        assert event.timestamp != ""
        assert event.source == ""

    def test_subscriber_count(self) -> None:
        """Test the subscriber_count property."""
        assert self.bus.subscriber_count == 0
        self.bus.subscribe("a.*", self._handler)
        self.bus.subscribe("b.*", self._handler)
        assert self.bus.subscriber_count == 2

    def test_publish_count(self) -> None:
        """Test the publish_count property."""
        assert self.bus.publish_count == 0
        self.bus.publish(Event(type="a"))
        self.bus.publish(Event(type="b"))
        assert self.bus.publish_count == 2

    def test_clear(self) -> None:
        """Test clearing all subscriptions."""
        self.bus.subscribe("a.*", self._handler)
        self.bus.subscribe("b.*", self._handler)
        assert self.bus.subscriber_count == 2
        self.bus.clear()
        assert self.bus.subscriber_count == 0

    def test_list_subscriptions(self) -> None:
        """Test listing active subscriptions."""
        sub = self.bus.subscribe("test.*", self._handler, description="Test handler")
        subs = self.bus.list_subscriptions()
        assert len(subs) == 1
        assert subs[0].pattern == "test.*"
        assert subs[0].description == "Test handler"

    def test_event_is_frozen(self) -> None:
        """Test that Event is frozen (immutable)."""
        event = Event(type="test.event", data={"key": "value"})
        with pytest.raises(AttributeError):
            event.type = "modified"  # type: ignore[misc]
