"""In-process asyncio event bus and SSE serialization."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict

from nine_bars.domain.events import DomainEvent

logger = logging.getLogger(__name__)


def serialize(event: DomainEvent) -> str:
    """Serialize a domain event to the SSE payload string."""
    return json.dumps({"type": type(event).__name__, "data": asdict(event)})


class EventBus:
    """Fan out events to per-type subscribers; publishing is fire-and-forget."""

    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], set[asyncio.Queue[DomainEvent]]] = {}

    def publish(self, event: DomainEvent) -> None:
        """Deliver ``event`` to every subscriber registered for its type."""
        logger.info("event %s", type(event).__name__)
        for event_type, queues in self._subscribers.items():
            if isinstance(event, event_type):
                for queue in queues:
                    queue.put_nowait(event)

    async def stream(
        self, *event_types: type[DomainEvent], ready: asyncio.Event | None = None
    ) -> AsyncIterator[DomainEvent]:
        """Yield events of the given types as they are published.

        When ``ready`` is provided it is set once the subscription is registered,
        giving callers a deterministic signal that publishing is safe.
        """
        queue: asyncio.Queue[DomainEvent] = asyncio.Queue()
        for event_type in event_types:
            self._subscribers.setdefault(event_type, set()).add(queue)
        if ready is not None:
            ready.set()
        try:
            while True:
                yield await queue.get()
        finally:
            for event_type in event_types:
                self._subscribers[event_type].discard(queue)
