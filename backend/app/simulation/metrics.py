"""Metrics collection for the simulation."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, NamedTuple
from enum import Enum, auto


class MissType(Enum):
    """Types of miss events."""
    NO_BATTERY = auto()       # Station had no batteries available
    PARTIAL_CHARGE = auto()   # Battery wasn't fully charged


class MissEvent(NamedTuple):
    """Record of a miss event."""
    timestamp: float
    scooter_id: str
    station_id: str
    miss_type: MissType
    charge_level: Optional[float] = None  # For partial charge misses


class SwapEvent(NamedTuple):
    """Record of a swap event."""
    timestamp: float
    scooter_id: str
    station_id: str
    old_battery_level: float
    new_battery_level: float
    was_partial: bool  # True if new battery wasn't fully charged


@dataclass
class MetricsCollector:
    """Collects and aggregates simulation metrics."""

    # Miss tracking
    miss_events: List[MissEvent] = field(default_factory=list)

    # Swap tracking
    swap_events: List[SwapEvent] = field(default_factory=list)
    swaps_per_station: Dict[str, int] = field(default_factory=dict)

    # Wait time tracking (scooter_id -> start time)
    wait_start_times: Dict[str, float] = field(default_factory=dict)
    wait_durations: List[float] = field(default_factory=list)

    # Time series data for charts
    miss_rate_history: List[tuple] = field(default_factory=list)  # (time, rate)
    sample_interval: float = 60.0  # Sample every 60 seconds
    last_sample_time: float = 0.0

    def record_no_battery_miss(
        self,
        time: float,
        scooter_id: str,
        station_id: str
    ) -> None:
        """Record when scooter couldn't get any battery."""
        self.miss_events.append(MissEvent(
            timestamp=time,
            scooter_id=scooter_id,
            station_id=station_id,
            miss_type=MissType.NO_BATTERY
        ))
        self.wait_start_times[scooter_id] = time

    def record_partial_charge_miss(
        self,
        time: float,
        scooter_id: str,
        station_id: str,
        charge_level: float
    ) -> None:
        """Record when scooter got a non-full battery."""
        self.miss_events.append(MissEvent(
            timestamp=time,
            scooter_id=scooter_id,
            station_id=station_id,
            miss_type=MissType.PARTIAL_CHARGE,
            charge_level=charge_level
        ))

    def record_swap(
        self,
        time: float,
        scooter_id: str,
        station_id: str,
        old_battery_level: float,
        new_battery_level: float
    ) -> None:
        """Record a completed swap."""
        was_partial = new_battery_level < 0.9999  # Not fully charged

        self.swap_events.append(SwapEvent(
            timestamp=time,
            scooter_id=scooter_id,
            station_id=station_id,
            old_battery_level=old_battery_level,
            new_battery_level=new_battery_level,
            was_partial=was_partial
        ))

        self.swaps_per_station[station_id] = \
            self.swaps_per_station.get(station_id, 0) + 1

        # Record partial charge as miss
        if was_partial:
            self.record_partial_charge_miss(time, scooter_id, station_id, new_battery_level)

        # Calculate wait time if applicable
        if scooter_id in self.wait_start_times:
            wait_duration = time - self.wait_start_times[scooter_id]
            self.wait_durations.append(wait_duration)
            del self.wait_start_times[scooter_id]

    def sample_metrics(self, current_time: float) -> None:
        """Sample current miss rate for time series."""
        if current_time - self.last_sample_time >= self.sample_interval:
            rate = self.current_miss_rate
            self.miss_rate_history.append((current_time, rate))
            self.last_sample_time = current_time

    @property
    def total_swaps(self) -> int:
        """Total number of swaps."""
        return len(self.swap_events)

    @property
    def total_misses(self) -> int:
        """Total number of misses (both types)."""
        return len(self.miss_events)

    @property
    def no_battery_misses(self) -> int:
        """Count of no-battery-available misses."""
        return sum(1 for m in self.miss_events if m.miss_type == MissType.NO_BATTERY)

    @property
    def partial_charge_misses(self) -> int:
        """Count of partial-charge misses."""
        return sum(1 for m in self.miss_events if m.miss_type == MissType.PARTIAL_CHARGE)

    @property
    def current_miss_rate(self) -> float:
        """Current miss rate (misses / swaps)."""
        if self.total_swaps == 0:
            return 0.0
        return self.total_misses / self.total_swaps

    @property
    def average_wait_time(self) -> float:
        """Average wait time in seconds."""
        if not self.wait_durations:
            return 0.0
        return sum(self.wait_durations) / len(self.wait_durations)

    @property
    def max_wait_time(self) -> float:
        """Maximum wait time in seconds."""
        if not self.wait_durations:
            return 0.0
        return max(self.wait_durations)

    def compile(self) -> dict:
        """Compile all metrics into a summary dictionary."""
        return {
            "total_swaps": self.total_swaps,
            "total_misses": self.total_misses,
            "no_battery_misses": self.no_battery_misses,
            "partial_charge_misses": self.partial_charge_misses,
            "miss_rate": self.current_miss_rate,
            "no_battery_miss_rate": self.no_battery_misses / max(1, self.total_swaps),
            "partial_charge_miss_rate": self.partial_charge_misses / max(1, self.total_swaps),
            "average_wait_time": self.average_wait_time,
            "max_wait_time": self.max_wait_time,
            "swaps_per_station": dict(self.swaps_per_station),
            "miss_rate_history": self.miss_rate_history,
        }

    def get_current_metrics(self) -> dict:
        """Get current metrics for real-time display."""
        return {
            "total_swaps": self.total_swaps,
            "total_misses": self.total_misses,
            "miss_rate": self.current_miss_rate,
            "no_battery_misses": self.no_battery_misses,
            "partial_charge_misses": self.partial_charge_misses,
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.miss_events.clear()
        self.swap_events.clear()
        self.swaps_per_station.clear()
        self.wait_start_times.clear()
        self.wait_durations.clear()
        self.miss_rate_history.clear()
        self.last_sample_time = 0.0
