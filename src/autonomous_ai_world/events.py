"""Synchronous event distribution for deterministic world updates."""

from __future__ import annotations

from collections.abc import Callable

from autonomous_ai_world.models import Event

EventHandler = Callable[[Event], None]


class EventBus:
    """Publishes world facts and retains an observer/debug event log."""

    def __init__(self) -> None:
        self._subscribers: list[EventHandler] = []
        self._history: list[Event] = []

    @property
    def history(self) -> tuple[Event, ...]:
        return tuple(self._history)

    def subscribe(self, handler: EventHandler) -> Callable[[], None]:
        self._subscribers.append(handler)

        def unsubscribe() -> None:
            if handler in self._subscribers:
                self._subscribers.remove(handler)

        return unsubscribe

    def publish(self, event: Event) -> None:
        self._history.append(event)
        for handler in tuple(self._subscribers):
            handler(event)

