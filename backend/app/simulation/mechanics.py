"""Movement, charging, and swapping mechanics for the simulation.

This module provides functions for scheduling scooter movements and
calculating energy consumption. Movement behavior is delegated to
pluggable strategies via the world's movement_strategy and
station_seeking_behavior attributes.
"""

from typing import Tuple, TYPE_CHECKING

from app.models.entities import Position, Scooter, ScooterState

if TYPE_CHECKING:
    from app.models.entities import WorldState
    from app.simulation.scheduler import EventScheduler
    from app.simulation.events import Event


def schedule_move(
    scooter: Scooter,
    world: "WorldState",
    scheduler: "EventScheduler"
) -> Tuple["Event", float]:
    """Schedule next move for a scooter using the world's movement strategy.

    This is the primary entry point for scheduling scooter movement.
    It delegates destination selection to world.movement_strategy.

    Args:
        scooter: The scooter to schedule a move for
        world: Current world state (contains movement_strategy)
        scheduler: Event scheduler

    Returns:
        Tuple of (ScooterMoveEvent, scheduled_time)
    """
    from app.simulation.events import ScooterMoveEvent
    from app.simulation.movement_strategies import DEFAULT_MOVEMENT_STRATEGY

    # Use world's strategy or fall back to default
    strategy = world.movement_strategy or DEFAULT_MOVEMENT_STRATEGY

    # Get next destination from strategy
    next_pos = strategy.get_next_destination(scooter, world, scheduler)

    # Calculate travel time
    distance = scooter.position.distance_to(next_pos)
    travel_time = scooter.travel_time(distance) if distance > 0 else 0.1

    event = ScooterMoveEvent(scooter_id=scooter.id, new_position=next_pos)
    return (event, world.current_time + travel_time)


def schedule_move_toward_station(
    scooter: Scooter,
    world: "WorldState",
    scheduler: "EventScheduler"
) -> Tuple["Event", float]:
    """Schedule move toward target station using station-seeking behavior.

    Uses world.station_seeking_behavior for pathfinding toward the
    scooter's target station. Falls back to greedy behavior if not set.

    Args:
        scooter: The scooter traveling to a station
        world: Current world state (contains station_seeking_behavior)
        scheduler: Event scheduler

    Returns:
        Tuple of (ScooterMoveEvent, scheduled_time)
    """
    from app.simulation.events import ScooterMoveEvent
    from app.simulation.movement_strategies import DEFAULT_STATION_SEEKING_BEHAVIOR

    if not scooter.target_position:
        # No target, use normal movement strategy
        return schedule_move(scooter, world, scheduler)

    # Use world's station seeking behavior or fall back to default
    behavior = world.station_seeking_behavior or DEFAULT_STATION_SEEKING_BEHAVIOR

    next_pos = behavior.get_next_step_toward_station(scooter, world, scheduler)

    distance = scooter.position.distance_to(next_pos)
    travel_time = scooter.travel_time(distance) if distance > 0 else 0.0

    event = ScooterMoveEvent(scooter_id=scooter.id, new_position=next_pos)
    return (event, world.current_time + travel_time)


def calculate_energy_consumption(distance: float, consumption_rate: float) -> float:
    """Calculate energy consumed for traveling a distance.

    Args:
        distance: Distance traveled in grid units
        consumption_rate: Energy consumption rate in kWh per grid unit

    Returns:
        Energy consumed in kWh
    """
    return distance * consumption_rate


def calculate_charge_time(
    current_charge: float,
    capacity: float,
    charge_rate_kw: float
) -> float:
    """Calculate time in seconds to fully charge a battery.

    Args:
        current_charge: Current charge level in kWh
        capacity: Battery capacity in kWh
        charge_rate_kw: Charging rate in kW

    Returns:
        Time to full charge in seconds
    """
    remaining = capacity - current_charge
    if remaining <= 0:
        return 0.0
    # remaining (kWh) / charge_rate (kW) = hours, * 3600 = seconds
    return (remaining / charge_rate_kw) * 3600
