"""Time utilities for simulation time-of-day awareness.

This module provides functions for converting between simulation time
(in seconds) and human-readable time-of-day values.

IMPORTANT: Simulation time directly represents time-of-day in the simulated
world. For example:
- 0 seconds = 00:00 (midnight)
- 3600 seconds = 01:00
- 14400 seconds = 04:00
- 86400 seconds = 00:00 (next day)

The time_scale parameter is NOT used for time-of-day calculations. It only
affects how fast simulation time progresses relative to real wall-clock time
when running the simulation.
"""

from dataclasses import dataclass


@dataclass
class SimulationTimeInfo:
    """Parsed simulation time information."""
    simulation_seconds: float    # Raw simulation time
    day: int                     # Day number (0-indexed)
    hour: float                  # Hour of day (0-24)
    minute: float                # Minute of hour (0-60)
    formatted: str               # "Day 1, 08:30"


def parse_simulation_time(
    simulation_seconds: float,
    time_scale: float = 60.0  # Unused, kept for API compatibility
) -> SimulationTimeInfo:
    """Convert simulation time to structured time info.

    Args:
        simulation_seconds: Simulation time in seconds
        time_scale: Unused, kept for API compatibility

    Returns:
        SimulationTimeInfo with parsed components
    """
    total_hours = simulation_seconds / 3600

    day = int(total_hours // 24)
    hour_of_day = total_hours % 24
    hour = int(hour_of_day)
    minute = (hour_of_day - hour) * 60

    formatted = f"Day {day + 1}, {hour:02d}:{int(minute):02d}"

    return SimulationTimeInfo(
        simulation_seconds=simulation_seconds,
        day=day,
        hour=hour_of_day,
        minute=minute,
        formatted=formatted
    )


def simulation_time_from_hour(
    day: int,
    hour: float,
    time_scale: float = 60.0  # Unused, kept for API compatibility
) -> float:
    """Convert day and hour to simulation time.

    Args:
        day: Day number (0-indexed)
        hour: Hour of day (0-24)
        time_scale: Unused, kept for API compatibility

    Returns:
        Simulation time in seconds
    """
    total_hours = day * 24 + hour
    return total_hours * 3600


def get_next_midnight(
    current_simulation_time: float,
    time_scale: float = 60.0  # Unused, kept for API compatibility
) -> float:
    """Get simulation time of next midnight.

    Args:
        current_simulation_time: Current simulation time in seconds
        time_scale: Unused, kept for API compatibility

    Returns:
        Simulation time at next midnight (00:00)
    """
    info = parse_simulation_time(current_simulation_time)
    next_day = info.day + 1
    return simulation_time_from_hour(next_day, 0.0)


def get_hour_of_day(
    simulation_time: float,
    time_scale: float = 60.0  # Unused, kept for API compatibility
) -> float:
    """Get hour of day from simulation time.

    Args:
        simulation_time: Simulation time in seconds
        time_scale: Unused, kept for API compatibility

    Returns:
        Hour of day as float (0-24)
    """
    total_hours = simulation_time / 3600
    return total_hours % 24


def get_day_number(
    simulation_time: float,
    time_scale: float = 60.0  # Unused, kept for API compatibility
) -> int:
    """Get day number from simulation time.

    Args:
        simulation_time: Simulation time in seconds
        time_scale: Unused, kept for API compatibility

    Returns:
        Day number (0-indexed)
    """
    total_hours = simulation_time / 3600
    return int(total_hours // 24)


def hours_until(
    target_hour: float,
    current_hour: float
) -> float:
    """Calculate hours until target hour (handles day wrap).

    Args:
        target_hour: Target hour (0-24)
        current_hour: Current hour (0-24)

    Returns:
        Hours until target (always positive, wraps at 24)
    """
    if target_hour > current_hour:
        return target_hour - current_hour
    else:
        return (24 - current_hour) + target_hour


def simulation_seconds_until_hour(
    current_simulation_time: float,
    target_hour: float,
    time_scale: float = 60.0  # Unused, kept for API compatibility
) -> float:
    """Calculate simulation seconds until a target hour of day.

    Args:
        current_simulation_time: Current simulation time
        target_hour: Target hour (0-24)
        time_scale: Unused, kept for API compatibility

    Returns:
        Simulation seconds until target hour
    """
    current_hour = get_hour_of_day(current_simulation_time)
    hours = hours_until(target_hour, current_hour)
    return hours * 3600
