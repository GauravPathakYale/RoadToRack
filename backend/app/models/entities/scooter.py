"""Scooter entity for the simulation."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from .position import Position


class ScooterState(Enum):
    """Possible states for a scooter."""
    MOVING = auto()                    # Random walk
    TRAVELING_TO_STATION = auto()      # Going to station for swap
    SWAPPING = auto()                  # At station, performing swap
    WAITING_FOR_BATTERY = auto()       # At station, no battery available


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
        }
