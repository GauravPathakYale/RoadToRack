"""Activity strategy pattern for scooter operating schedules.

This module provides an abstract base class for activity strategies and
concrete implementations. The strategy pattern allows flexible control
over when scooters are active vs idle.

Available strategies:
- AlwaysActiveStrategy: Scooters never go idle (default, current behavior)
- ScheduledActivityStrategy: Time-based schedules with distance limits
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.entities import Scooter, WorldState
    from app.simulation.scheduler import EventScheduler


class ActivityStrategyType(str, Enum):
    """Enum for available activity strategy types."""
    ALWAYS_ACTIVE = "always_active"
    SCHEDULED = "scheduled"


class ActivityDecision(Enum):
    """Decision about scooter activity state."""
    CONTINUE_ACTIVE = "continue_active"    # Scooter should remain active
    GO_IDLE = "go_idle"                    # Scooter should become idle
    SWAP_THEN_IDLE = "swap_then_idle"      # Low battery, swap first then idle


@dataclass
class ActivityCheckResult:
    """Result of an activity check."""
    decision: ActivityDecision
    reason: str
    wake_up_time: Optional[float] = None   # When to wake up (if going idle)


class ActivityStrategy(ABC):
    """Abstract base class for scooter activity strategies.

    Activity strategies determine whether a scooter should be active
    (moving, seeking stations) or idle (resting). They work alongside
    MovementStrategy to provide time-based behavior control.

    Subclasses must implement:
    - check_activity(): Determine if scooter should be active
    - should_wake_up(): Check if idle scooter should wake
    """

    @abstractmethod
    def check_activity(
        self,
        scooter: "Scooter",
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> ActivityCheckResult:
        """Check whether scooter should be active or idle.

        Called before scheduling new movement events. If the scooter
        should go idle, returns GO_IDLE or SWAP_THEN_IDLE.

        Args:
            scooter: The scooter to check
            world: Current world state
            scheduler: Event scheduler (provides current time)

        Returns:
            ActivityCheckResult with decision and optional wake_up_time
        """
        pass

    @abstractmethod
    def should_wake_up(
        self,
        scooter: "Scooter",
        world: "WorldState",
        current_time: float
    ) -> bool:
        """Check if an idle scooter should wake up.

        Args:
            scooter: The idle scooter
            world: Current world state
            current_time: Current simulation time

        Returns:
            True if scooter should wake up, False otherwise
        """
        pass

    def on_day_reset(
        self,
        scooter: "Scooter",
        world: "WorldState",
        new_day: int
    ) -> None:
        """Called at midnight to reset daily counters.

        Override to reset daily tracking like distance traveled.

        Args:
            scooter: The scooter being reset
            world: Current world state
            new_day: The new day number (0-indexed)
        """
        pass


class AlwaysActiveStrategy(ActivityStrategy):
    """Default strategy - scooters are always active.

    This preserves the current behavior where scooters never
    voluntarily go idle.
    """

    def check_activity(
        self,
        scooter: "Scooter",
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> ActivityCheckResult:
        """Always returns CONTINUE_ACTIVE."""
        return ActivityCheckResult(
            decision=ActivityDecision.CONTINUE_ACTIVE,
            reason="Always active strategy"
        )

    def should_wake_up(
        self,
        scooter: "Scooter",
        world: "WorldState",
        current_time: float
    ) -> bool:
        """Never called since scooters never go idle."""
        return True

    def on_day_reset(
        self,
        scooter: "Scooter",
        world: "WorldState",
        new_day: int
    ) -> None:
        """Reset daily distance counter."""
        scooter.distance_traveled_today = 0.0


class ScheduledActivityStrategy(ActivityStrategy):
    """Time-based activity schedule with distance limits.

    Scooters are active during specified hours and up to a
    daily distance limit. When going idle, they first swap
    batteries if below threshold.

    Attributes:
        activity_start_hour: Hour (0-23) when activity starts
        activity_end_hour: Hour (0-23) when activity ends
        max_distance_per_day_km: Maximum daily distance in real-world km
        low_battery_threshold: Battery level to trigger pre-idle swap
        meters_per_grid_unit: Scale factor for distance conversion
        time_scale: Real seconds per simulation second
    """

    def __init__(
        self,
        activity_start_hour: float = 8.0,    # 8:00 AM
        activity_end_hour: float = 20.0,     # 8:00 PM
        max_distance_per_day_km: Optional[float] = None,  # None = unlimited
        low_battery_threshold: float = 0.3,   # 30%
        meters_per_grid_unit: float = 100.0,
        time_scale: float = 60.0              # sim seconds per real second
    ):
        self.activity_start_hour = activity_start_hour
        self.activity_end_hour = activity_end_hour
        self.max_distance_per_day_km = max_distance_per_day_km
        self.low_battery_threshold = low_battery_threshold
        self.meters_per_grid_unit = meters_per_grid_unit
        self.time_scale = time_scale

    def _get_time_of_day(self, simulation_time: float) -> float:
        """Convert simulation time to hour of day (0-24).

        The simulation time directly represents time-of-day in the
        simulated world. We do NOT multiply by time_scale here - that
        factor is for real-world speed conversion, not time-of-day.

        Args:
            simulation_time: Simulation time in seconds

        Returns:
            Hour of day as float (e.g., 8.5 = 8:30 AM)
        """
        # Simulation seconds -> hours -> hour of day
        total_hours = simulation_time / 3600
        hour_of_day = total_hours % 24
        return hour_of_day

    def _get_day_number(self, simulation_time: float) -> int:
        """Get the current day number (0-indexed).

        Args:
            simulation_time: Simulation time in seconds

        Returns:
            Day number starting from 0
        """
        total_hours = simulation_time / 3600
        return int(total_hours // 24)

    def _is_within_active_hours(self, hour_of_day: float) -> bool:
        """Check if hour is within active period.

        Handles overnight schedules (e.g., 22:00 to 06:00).
        """
        if self.activity_start_hour <= self.activity_end_hour:
            # Normal schedule (e.g., 08:00 to 20:00)
            return self.activity_start_hour <= hour_of_day < self.activity_end_hour
        else:
            # Overnight schedule (e.g., 22:00 to 06:00)
            return hour_of_day >= self.activity_start_hour or hour_of_day < self.activity_end_hour

    def _distance_to_km(self, grid_units: float) -> float:
        """Convert grid units to kilometers."""
        return (grid_units * self.meters_per_grid_unit) / 1000

    def _has_exceeded_daily_distance(self, scooter: "Scooter") -> bool:
        """Check if scooter has exceeded daily distance limit."""
        if self.max_distance_per_day_km is None:
            return False
        km_traveled = self._distance_to_km(scooter.distance_traveled_today)
        return km_traveled >= self.max_distance_per_day_km

    def _calculate_wake_up_time(
        self,
        current_time: float,
        reason: str
    ) -> float:
        """Calculate simulation time when scooter should wake up.

        Args:
            current_time: Current simulation time in seconds
            reason: Why going idle (affects wake time calculation)

        Returns:
            Simulation time to wake up (in seconds)
        """
        hour_of_day = self._get_time_of_day(current_time)

        if reason == "outside_hours":
            # Wake at next activity start
            if hour_of_day >= self.activity_end_hour:
                # After end time, wake tomorrow at start time
                hours_until_wake = (24 - hour_of_day) + self.activity_start_hour
            else:
                # Before start time, wake at start time today
                hours_until_wake = self.activity_start_hour - hour_of_day
        else:
            # Distance limit - wake at midnight then check if within active hours
            hours_until_midnight = 24 - hour_of_day
            hours_until_wake = hours_until_midnight + self.activity_start_hour

        # Convert hours to simulation seconds (no time_scale - simulation time IS the time-of-day)
        sim_seconds_until_wake = hours_until_wake * 3600

        return current_time + sim_seconds_until_wake

    def check_activity(
        self,
        scooter: "Scooter",
        world: "WorldState",
        scheduler: "EventScheduler"
    ) -> ActivityCheckResult:
        """Check if scooter should be active based on time and distance."""
        current_time = world.current_time
        hour_of_day = self._get_time_of_day(current_time)

        # Check time-based constraints
        if not self._is_within_active_hours(hour_of_day):
            wake_time = self._calculate_wake_up_time(current_time, "outside_hours")

            # Check if battery is low - need to swap first
            battery = world.get_battery(scooter.battery_id)
            if battery and battery.charge_level < self.low_battery_threshold:
                return ActivityCheckResult(
                    decision=ActivityDecision.SWAP_THEN_IDLE,
                    reason=f"Outside active hours ({hour_of_day:.1f}h), low battery",
                    wake_up_time=wake_time
                )

            return ActivityCheckResult(
                decision=ActivityDecision.GO_IDLE,
                reason=f"Outside active hours ({hour_of_day:.1f}h)",
                wake_up_time=wake_time
            )

        # Check distance-based constraints
        if self._has_exceeded_daily_distance(scooter):
            wake_time = self._calculate_wake_up_time(current_time, "distance_limit")

            # Check if battery is low - need to swap first
            battery = world.get_battery(scooter.battery_id)
            if battery and battery.charge_level < self.low_battery_threshold:
                return ActivityCheckResult(
                    decision=ActivityDecision.SWAP_THEN_IDLE,
                    reason="Daily distance limit reached, low battery",
                    wake_up_time=wake_time
                )

            return ActivityCheckResult(
                decision=ActivityDecision.GO_IDLE,
                reason="Daily distance limit reached",
                wake_up_time=wake_time
            )

        return ActivityCheckResult(
            decision=ActivityDecision.CONTINUE_ACTIVE,
            reason="Within active hours and distance limit"
        )

    def should_wake_up(
        self,
        scooter: "Scooter",
        world: "WorldState",
        current_time: float
    ) -> bool:
        """Check if idle scooter should wake up."""
        # Check explicit wake time
        if scooter.idle_until and current_time >= scooter.idle_until:
            # Verify we're within active hours
            hour_of_day = self._get_time_of_day(current_time)
            if self._is_within_active_hours(hour_of_day):
                # Also verify distance hasn't been exceeded (shouldn't happen after reset)
                return not self._has_exceeded_daily_distance(scooter)
        return False

    def on_day_reset(
        self,
        scooter: "Scooter",
        world: "WorldState",
        new_day: int
    ) -> None:
        """Reset daily distance counter at midnight."""
        scooter.distance_traveled_today = 0.0


def create_activity_strategy(
    strategy_type: ActivityStrategyType,
    **kwargs
) -> ActivityStrategy:
    """Factory function to create activity strategies by type.

    Args:
        strategy_type: The type of strategy to create
        **kwargs: Additional arguments for the strategy constructor

    Returns:
        A new instance of the requested strategy type

    Raises:
        ValueError: If strategy_type is not recognized
    """
    if strategy_type == ActivityStrategyType.ALWAYS_ACTIVE:
        return AlwaysActiveStrategy()
    elif strategy_type == ActivityStrategyType.SCHEDULED:
        return ScheduledActivityStrategy(**kwargs)
    else:
        raise ValueError(f"Unknown activity strategy type: {strategy_type}")


# Default strategy for convenience
DEFAULT_ACTIVITY_STRATEGY = AlwaysActiveStrategy()
