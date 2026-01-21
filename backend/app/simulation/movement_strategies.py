"""Movement strategy pattern for pluggable scooter movement behaviors.

This module provides an abstract base class for movement strategies and
concrete implementations. The strategy pattern allows swapping movement
behaviors without changing the event processing logic.

Available strategies:
- RandomWalkStrategy: Scooters move randomly to neighboring cells
- DirectedMovementStrategy: Scooters receive destinations from external sources

Future extensions:
- RideSharingStrategy: External API assigns pickup/dropoff locations
- HotspotStrategy: Scooters gravitate toward high-demand areas
- PatrolStrategy: Scooters follow predefined routes
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Optional, Dict

from app.models.entities import Position, Scooter

if TYPE_CHECKING:
    from app.models.entities import WorldState
    from app.simulation.scheduler import EventScheduler


class MovementStrategyType(str, Enum):
    """Enum for available movement strategy types."""
    RANDOM_WALK = "random_walk"
    DIRECTED = "directed"


class MovementStrategy(ABC):
    """Abstract base class for scooter movement strategies.

    Movement strategies determine where a scooter should move next when
    it's in the MOVING state. They don't handle station-seeking behavior,
    which is managed by StationSeekingBehavior.

    Subclasses must implement:
    - get_next_destination(): Return the next position for a scooter
    """

    @abstractmethod
    def get_next_destination(
        self,
        scooter: Scooter,
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> Position:
        """Determine the next position the scooter should move to.

        Args:
            scooter: The scooter that needs a destination
            world: Current world state
            scheduler: Event scheduler (provides RNG for reproducibility)

        Returns:
            The next Position the scooter should move toward
        """
        pass

    def on_scooter_activated(
        self,
        scooter: Scooter,
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> None:
        """Called when a scooter starts moving (e.g., after battery swap).

        Override this to perform any initialization needed when a scooter
        begins its movement cycle.

        Args:
            scooter: The scooter that just started moving
            world: Current world state
            scheduler: Event scheduler
        """
        pass


class RandomWalkStrategy(MovementStrategy):
    """Random walk movement strategy.

    Scooters move to a randomly selected neighboring cell (4-directional).
    This is the default behavior from the original implementation.
    """

    def get_next_destination(
        self,
        scooter: Scooter,
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> Position:
        """Return a random neighboring position."""
        rng = scheduler.get_rng()
        neighbors = scooter.position.neighbors(world.grid_width, world.grid_height)

        if not neighbors:
            # Edge case: no valid neighbors (shouldn't happen with proper grid)
            return scooter.position

        idx = rng.integers(0, len(neighbors))
        return neighbors[idx]


class DirectedMovementStrategy(MovementStrategy):
    """Directed movement strategy for external destination assignment.

    Scooters receive destinations from an external source (e.g., a ride-sharing
    dispatch system). If no destination is assigned, the scooter idles.

    Usage:
        strategy = DirectedMovementStrategy()
        strategy.set_destination("scooter_1", Position(50, 50))
        # Scooter will now move toward (50, 50)

        strategy.clear_destination("scooter_1")
        # Scooter will now idle
    """

    def __init__(self):
        self._destinations: Dict[str, Position] = {}
        self._idle_behavior: Optional[MovementStrategy] = None

    def set_idle_behavior(self, strategy: MovementStrategy) -> None:
        """Set fallback behavior when no destination is assigned.

        Args:
            strategy: Strategy to use when scooter has no destination.
                     If None, scooter stays in place.
        """
        self._idle_behavior = strategy

    def set_destination(self, scooter_id: str, destination: Position) -> None:
        """Assign a destination to a scooter.

        Args:
            scooter_id: ID of the scooter to assign destination to
            destination: Target position for the scooter
        """
        self._destinations[scooter_id] = destination

    def clear_destination(self, scooter_id: str) -> None:
        """Clear a scooter's assigned destination.

        Args:
            scooter_id: ID of the scooter to clear destination for
        """
        self._destinations.pop(scooter_id, None)

    def get_destination(self, scooter_id: str) -> Optional[Position]:
        """Get a scooter's currently assigned destination.

        Args:
            scooter_id: ID of the scooter

        Returns:
            The assigned destination, or None if no destination is set
        """
        return self._destinations.get(scooter_id)

    def has_destination(self, scooter_id: str) -> bool:
        """Check if a scooter has an assigned destination.

        Args:
            scooter_id: ID of the scooter

        Returns:
            True if scooter has a destination, False otherwise
        """
        return scooter_id in self._destinations

    def get_next_destination(
        self,
        scooter: Scooter,
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> Position:
        """Return next step toward assigned destination, or idle position."""
        target = self._destinations.get(scooter.id)

        if target is None:
            # No destination assigned
            if self._idle_behavior:
                return self._idle_behavior.get_next_destination(
                    scooter, world, scheduler
                )
            # Stay in place if no idle behavior
            return scooter.position

        current = scooter.position

        # Check if already at destination
        if current == target:
            # Arrived - clear destination and idle
            self.clear_destination(scooter.id)
            if self._idle_behavior:
                return self._idle_behavior.get_next_destination(
                    scooter, world, scheduler
                )
            return current

        # Calculate next step toward destination (greedy single-step)
        dx = target.x - current.x
        dy = target.y - current.y

        if dx != 0:
            next_pos = Position(current.x + (1 if dx > 0 else -1), current.y)
        elif dy != 0:
            next_pos = Position(current.x, current.y + (1 if dy > 0 else -1))
        else:
            next_pos = current

        return next_pos

    def on_scooter_activated(
        self,
        scooter: Scooter,
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> None:
        """Clear any stale destination when scooter starts moving."""
        # Optionally clear old destination on reactivation
        # This can be customized based on dispatch system requirements
        pass


class StationSeekingBehavior(ABC):
    """Abstract base class for station-seeking navigation behavior.

    This handles how a scooter navigates toward a target station when
    its battery is low. Separate from the main movement strategy.
    """

    @abstractmethod
    def get_next_step_toward_station(
        self,
        scooter: Scooter,
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> Position:
        """Determine next position when traveling to a station.

        Args:
            scooter: The scooter traveling to a station
            world: Current world state
            scheduler: Event scheduler

        Returns:
            Next position toward the target station
        """
        pass


class GreedyStationSeekingBehavior(StationSeekingBehavior):
    """Greedy pathfinding toward target station.

    Moves one step at a time, prioritizing X-axis movement first,
    then Y-axis. No obstacle avoidance.
    """

    def get_next_step_toward_station(
        self,
        scooter: Scooter,
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> Position:
        """Return next step toward target station using greedy pathfinding."""
        if not scooter.target_position:
            # No target - stay in place
            return scooter.position

        target = scooter.target_position
        current = scooter.position

        # Simple greedy movement toward target
        dx = target.x - current.x
        dy = target.y - current.y

        if dx != 0:
            next_pos = Position(current.x + (1 if dx > 0 else -1), current.y)
        elif dy != 0:
            next_pos = Position(current.x, current.y + (1 if dy > 0 else -1))
        else:
            next_pos = current  # Already at target

        return next_pos


def create_movement_strategy(strategy_type: MovementStrategyType) -> MovementStrategy:
    """Factory function to create movement strategies by type.

    Args:
        strategy_type: The type of strategy to create

    Returns:
        A new instance of the requested strategy type

    Raises:
        ValueError: If strategy_type is not recognized
    """
    if strategy_type == MovementStrategyType.RANDOM_WALK:
        return RandomWalkStrategy()
    elif strategy_type == MovementStrategyType.DIRECTED:
        return DirectedMovementStrategy()
    else:
        raise ValueError(f"Unknown movement strategy type: {strategy_type}")


# Default strategies for convenience
DEFAULT_MOVEMENT_STRATEGY = RandomWalkStrategy()
DEFAULT_STATION_SEEKING_BEHAVIOR = GreedyStationSeekingBehavior()
