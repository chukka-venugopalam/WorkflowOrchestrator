"""In-process event bus for publish/subscribe communication.

Provides typed events with pattern-based subscription.  The Event Bus
is the backbone for observability without coupling — components
communicate by publishing events, never by calling each other directly.

Event taxonomy (namespaced):
    ``workflow.*``, ``step.*``, ``state.*``, ``capability.*``,
    ``provider.*``, ``agent.*``, ``deployment.*``, ``plugin.*``,
    ``verification.*``, ``report.*``
"""

from __future__ import annotations

import fnmatch
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """A typed event in the event bus.

    Attributes:
        type: The event type string (e.g., ``workflow.started``).
        data: Arbitrary event payload.
        source: Name of the component that published the event.
        timestamp: ISO-8601 timestamp of when the event was created.
        event_id: Unique identifier for this event instance.
    """

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: str = ""
    event_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat())
        if not self.event_id:
            object.__setattr__(self, "event_id", uuid.uuid4().hex[:12])


@dataclass
class Subscription:
    """A subscription to events matching a pattern.

    Attributes:
        id: Unique subscription identifier.
        pattern: Event type pattern (supports glob: ``step.*``).
        handler: Callback invoked when a matching event is published.
        description: Optional human-readable description.
    """

    id: str
    pattern: str
    handler: EventHandler
    description: str = ""


class EventBus:
    """In-process publish/subscribe event bus.

    Supports:
    - Typed events with string type identifiers
    - Glob pattern matching (``step.*`` matches ``step.failed``)
    - Subscriber isolation (one exception doesn't affect others)
    - Synchronous publish with option for async subscribers

    Usage:
        >>> bus = EventBus()
        >>> sub = bus.subscribe("step.*", lambda e: print(e.type))
        >>> bus.publish(Event(type="step.completed", data={"step": "build"}))
        >>> bus.unsubscribe(sub)
    """

    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}
        self._publish_count: int = 0

    def subscribe(
        self,
        pattern: str,
        handler: EventHandler,
        description: str = "",
    ) -> Subscription:
        """Subscribe to events matching a pattern.

        Args:
            pattern: Event type pattern. Supports glob-style wildcards,
                e.g., ``step.*`` matches ``step.started``, ``step.failed``.
            handler: Callable that receives the Event.
            description: Optional description of this subscription.

        Returns:
            A Subscription object that can be used to unsubscribe.
        """
        sub_id = uuid.uuid4().hex[:8]
        subscription = Subscription(
            id=sub_id,
            pattern=pattern,
            handler=handler,
            description=description,
        )
        self._subscriptions[sub_id] = subscription
        logger.debug(
            "Subscribed '%s' to pattern '%s' (%s)",
            description or sub_id,
            pattern,
            handler.__name__ if hasattr(handler, "__name__") else "anonymous",
        )
        return subscription

    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove a subscription.

        Args:
            subscription: The Subscription object returned by ``subscribe()``.
        """
        self._subscriptions.pop(subscription.id, None)
        logger.debug("Unsubscribed '%s'", subscription.id)

    def unsubscribe_by_id(self, subscription_id: str) -> None:
        """Remove a subscription by its ID.

        Args:
            subscription_id: The ID of the subscription to remove.
        """
        self._subscriptions.pop(subscription_id, None)

    def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers.

        Each subscriber is called synchronously.  If a subscriber
        raises an exception, it is logged and other subscribers
        still receive the event (subscriber isolation).

        Args:
            event: The event to publish.
        """
        if not event.timestamp:
            object.__setattr__(event, "timestamp", datetime.now(timezone.utc).isoformat())
        if not event.event_id:
            object.__setattr__(event, "event_id", uuid.uuid4().hex[:12])

        self._publish_count += 1

        matched = False
        for sub in list(self._subscriptions.values()):
            if fnmatch.fnmatch(event.type, sub.pattern):
                matched = True
                try:
                    sub.handler(event)
                except Exception:
                    logger.exception(
                        "Subscriber '%s' (pattern='%s') raised exception handling event '%s'",
                        sub.id,
                        sub.pattern,
                        event.type,
                    )

        if not matched and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Event '%s' published with no matching subscribers", event.type)

    def publish_sync(self, event: Event) -> None:
        """Alias for ``publish()`` — synchronous publication.

        Args:
            event: The event to publish.
        """
        self.publish(event)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscriptions.clear()
        logger.debug("All subscriptions cleared")

    @property
    def subscriber_count(self) -> int:
        """Number of active subscriptions."""
        return len(self._subscriptions)

    @property
    def publish_count(self) -> int:
        """Total number of events published since creation."""
        return self._publish_count

    def list_subscriptions(self) -> list[Subscription]:
        """List all active subscriptions.

        Returns:
            List of active Subscription objects.
        """
        return list(self._subscriptions.values())
