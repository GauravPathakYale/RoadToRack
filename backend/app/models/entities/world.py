"""World state container for the simulation."""

from dataclasses import dataclass, field
from typing import Dict, Optional, TYPE_CHECKING, Any
import copy

from .battery import Battery
from .station import Station
from .scooter import Scooter

if TYPE_CHECKING:
    from app.simulation.metrics import MetricsCollector
    from app.simulation.movement_strategies import MovementStrategy, StationSeekingBehavior


@dataclass
class WorldState:
    """
    Complete simulation state at a point in time.
    Mutable during event processing, can be snapshotted for visualization.
    """
    current_time: float = 0.0
    batteries: Dict[str, Battery] = field(default_factory=dict)
    stations: Dict[str, Station] = field(default_factory=dict)
    scooters: Dict[str, Scooter] = field(default_factory=dict)

    # Grid dimensions
    grid_width: int = 100
    grid_height: int = 100

    # Scale factors for time-of-day awareness
    time_scale: float = 60.0  # Real seconds per simulation second
    meters_per_grid_unit: float = 100.0

    # Metrics collector (set by SimulationEngine)
    metrics: Optional[Any] = None  # Actually MetricsCollector, using Any to avoid circular import

    # Movement strategies (set by SimulationEngine)
    # Using Any to avoid circular import at runtime
    movement_strategy: Optional[Any] = None  # Actually MovementStrategy
    station_seeking_behavior: Optional[Any] = None  # Actually StationSeekingBehavior

    # Scooter groups metadata (for frontend visualization)
    scooter_groups: list = field(default_factory=list)  # List of {id, name, color, count}

    def snapshot(self) -> "WorldState":
        """Create a deep copy for visualization/logging."""
        return copy.deepcopy(self)

    def get_battery(self, battery_id: str) -> Optional[Battery]:
        """Get battery by ID."""
        return self.batteries.get(battery_id)

    def get_station(self, station_id: str) -> Optional[Station]:
        """Get station by ID."""
        return self.stations.get(station_id)

    def get_scooter(self, scooter_id: str) -> Optional[Scooter]:
        """Get scooter by ID."""
        return self.scooters.get(scooter_id)

    def find_nearest_station(self, position: "Position") -> Optional[Station]:
        """Find the station closest to given position."""
        from .position import Position

        nearest = None
        min_distance = float("inf")

        for station in self.stations.values():
            dist = position.distance_to(station.position)
            if dist < min_distance:
                min_distance = dist
                nearest = station

        return nearest

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_time": float(self.current_time),
            "grid_width": int(self.grid_width),
            "grid_height": int(self.grid_height),
            "scooters": [
                {**s.to_dict(), "battery_level": float(self.batteries[s.battery_id].charge_level)}
                for s in self.scooters.values()
            ],
            "stations": [
                s.to_dict(self.batteries) for s in self.stations.values()
            ],
            "batteries": [b.to_dict() for b in self.batteries.values()],
            "scooter_groups": self.scooter_groups,
        }
