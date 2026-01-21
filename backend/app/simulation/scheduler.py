"""Event scheduler using priority queue for discrete event simulation."""

import heapq
from typing import Optional, List, Callable, Any
from dataclasses import dataclass, field
import numpy as np

from app.models.entities import WorldState


# Global event counter for deterministic tie-breaking
_event_counter = 0


def next_event_id() -> int:
    """Generate a unique monotonic event ID."""
    global _event_counter
    _event_counter += 1
    return _event_counter


def reset_event_counter() -> None:
    """Reset event counter (for testing or new simulations)."""
    global _event_counter
    _event_counter = 0


@dataclass(order=True)
class ScheduledEvent:
    """Wrapper for events in the priority queue."""
    scheduled_time: float
    event_id: int = field(compare=True)
    event: Any = field(compare=False)  # The actual event object


class EventScheduler:
    """
    Manages the event queue and simulation time advancement.
    Uses a heap-based priority queue for O(log n) operations.
    """

    def __init__(self, max_time: float, random_seed: Optional[int] = None):
        self.max_time = max_time
        self._queue: List[ScheduledEvent] = []
        self._rng = np.random.default_rng(random_seed)
        self._observers: List[Callable[[WorldState, Any], None]] = []

    def schedule(self, event: Any, time: float) -> None:
        """Add an event to the queue at specified time."""
        scheduled = ScheduledEvent(
            scheduled_time=time,
            event_id=next_event_id(),
            event=event
        )
        heapq.heappush(self._queue, scheduled)

    def schedule_many(self, events: List[tuple]) -> None:
        """Add multiple (event, time) tuples to the queue."""
        for event, time in events:
            self.schedule(event, time)

    def next_event(self) -> Optional[tuple]:
        """
        Remove and return the next event as (event, time).
        Returns None if queue is empty.
        """
        if self._queue:
            scheduled = heapq.heappop(self._queue)
            return (scheduled.event, scheduled.scheduled_time)
        return None

    def peek_next_time(self) -> Optional[float]:
        """Look at next event time without removing it."""
        if self._queue:
            return self._queue[0].scheduled_time
        return None

    def is_empty(self) -> bool:
        """Check if event queue is empty."""
        return len(self._queue) == 0

    def clear(self) -> None:
        """Clear all pending events."""
        self._queue.clear()

    @property
    def pending_count(self) -> int:
        """Number of events in queue."""
        return len(self._queue)

    def get_rng(self) -> np.random.Generator:
        """Get the random number generator for reproducible randomness."""
        return self._rng

    def add_observer(self, observer: Callable[[WorldState, Any], None]) -> None:
        """Register an observer for state changes."""
        self._observers.append(observer)

    def remove_observer(self, observer: Callable[[WorldState, Any], None]) -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, world: WorldState, event: Any) -> None:
        """Notify all observers of a state change."""
        for observer in self._observers:
            try:
                observer(world, event)
            except Exception as e:
                print(f"Observer error: {e}")
