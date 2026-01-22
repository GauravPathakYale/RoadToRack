"""Scooter entity for the simulation."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

from .position import Position

if TYPE_CHECKING:
    from app.simulation.movement_strategies import MovementStrategy
    from app.simulation.activity_strategies import ActivityStrategy


class ScooterState(Enum):
    """Possible states for a scooter."""
    MOVING = auto()                    # Active movement (random walk or directed)
    TRAVELING_TO_STATION = auto()      # Going to station for swap
    SWAPPING = auto()                  # At station, performing swap
    WAITING_FOR_BATTERY = auto()       # At station, no battery available
    IDLE = auto()                      # Resting, not active (outside operating hours or distance limit)


@dataclass
class Scooter:
    """Electric scooter that moves on the grid and needs battery swaps."""
    id: str
    position: Position
    battery_id: str
    state: ScooterState
    speed: float                       # grid units per second
    consumption_rate: float            # kWh per grid unit traveled
    swap_threshold: float              # charge level (0-1) that triggers swap

    # Navigation state
    target_station_id: Optional[str] = None
    target_position: Optional[Position] = None

    # Per-scooter movement strategy (overrides world.movement_strategy if set)
    movement_strategy: Optional["MovementStrategy"] = None

    # Scooter group for visual distinction and shared config
    group_id: Optional[str] = None

    # Per-scooter activity strategy (overrides world.activity_strategy if set)
    activity_strategy: Optional["ActivityStrategy"] = None

    # Daily distance tracking (reset at midnight)
    distance_traveled_today: float = 0.0

    # Idle state tracking
    idle_until: Optional[float] = None  # Simulation time when scooter should wake up

    def needs_swap(self, battery_charge_level: float) -> bool:
        """Check if scooter needs to find a swap station."""
        return battery_charge_level < self.swap_threshold

    def travel_time(self, distance: float) -> float:
        """Calculate time to travel a given distance."""
        if distance <= 0:
            return 0.0
        return distance / self.speed

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "battery_id": self.battery_id,
            "state": self.state.name,
            "speed": float(self.speed),
            "target_station_id": self.target_station_id,
            "target_position": self.target_position.to_dict() if self.target_position else None,
            "group_id": self.group_id,
            "distance_traveled_today": self.distance_traveled_today,
        }
