"""Event bus for component decoupling.

Provides simple publish-subscribe pattern for events.
"""

import logging
from collections import defaultdict
from typing import Any, Callable, TYPE_CHECKING

from friday_ai.agent.events import AgentEvent, AgentEventType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Callable
else:
    from collections.abc import Callable


EventCallback = Callable[..., Any]


class EventBus:
    """Simple event bus for component communication."""

    def __init__(self):
        """Initialize event bus."""
        self._subscribers: defaultdict[str, list[EventCallback]] = defaultdict(list)

    def subscribe(self, event_type: AgentEventType, callback: EventCallback) -> None:
        """Subscribe to event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Callback function
        """
        self._subscribers[event_type].append(callback)

    async def publish(self, event: AgentEvent) -> None:
        """Publish event to all subscribers.

        Args:
            event: Event to publish
        """
        for callback in self._subscribers[event.type]:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

    def unsubscribe(self, event_type: AgentEventType, callback: EventCallback) -> None:
        """Unsubscribe from event type.

        Args:
            event_type: Type of event
            callback: Callback function
        """
        try:
            self._subscribers[event_type].remove(callback)
        except ValueError:
            pass
