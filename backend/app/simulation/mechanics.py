"""Movement, charging, and swapping mechanics for the simulation."""

from typing import Tuple, TYPE_CHECKING

from app.models.entities import Position, Scooter, ScooterState

if TYPE_CHECKING:
    from app.models.entities import WorldState
    from app.simulation.scheduler import EventScheduler


def schedule_random_move(
    scooter: Scooter,
    world: "WorldState",
    scheduler: "EventScheduler"
) -> Tuple["Event", float]:
    """Schedule next random walk step for a scooter."""
    from app.simulation.events import ScooterMoveEvent

    rng = scheduler.get_rng()
    neighbors = scooter.position.neighbors(world.grid_width, world.grid_height)

    if not neighbors:
        # Edge case: no valid neighbors (shouldn't happen with proper grid)
        next_pos = scooter.position
    else:
        idx = rng.integers(0, len(neighbors))
        next_pos = neighbors[idx]

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
    """Schedule move toward target station (greedy shortest path)."""
    from app.simulation.events import ScooterMoveEvent

    if not scooter.target_position:
        # No target, schedule random move instead
        return schedule_random_move(scooter, world, scheduler)

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

    distance = current.distance_to(next_pos)
    travel_time = scooter.travel_time(distance) if distance > 0 else 0.0

    event = ScooterMoveEvent(scooter_id=scooter.id, new_position=next_pos)
    return (event, world.current_time + travel_time)


def calculate_energy_consumption(distance: float, consumption_rate: float) -> float:
    """Calculate energy consumed for traveling a distance."""
    return distance * consumption_rate


def calculate_charge_time(
    current_charge: float,
    capacity: float,
    charge_rate_kw: float
) -> float:
    """Calculate time in seconds to fully charge a battery."""
    remaining = capacity - current_charge
    if remaining <= 0:
        return 0.0
    # remaining (kWh) / charge_rate (kW) = hours, * 3600 = seconds
    return (remaining / charge_rate_kw) * 3600
