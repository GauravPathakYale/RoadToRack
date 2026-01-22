"""Core simulation engine for battery swap station simulation."""

from dataclasses import dataclass, field
from typing import Optional, List, Callable, Any, Union
from enum import Enum, auto
import asyncio

from app.models.entities import (
    WorldState, Position, Battery, BatteryLocation,
    Station, Scooter, ScooterState
)
from app.simulation.scheduler import EventScheduler, reset_event_counter
from app.simulation.events import ScooterMoveEvent, BatteryChargingTickEvent
from app.simulation.mechanics import schedule_move
from app.simulation.metrics import MetricsCollector
from app.simulation.movement_strategies import (
    MovementStrategy,
    StationSeekingBehavior,
    MovementStrategyType,
    RandomWalkStrategy,
    GreedyStationSeekingBehavior,
    create_movement_strategy,
)
from app.simulation.activity_strategies import (
    ActivityStrategy,
    ActivityStrategyType,
    AlwaysActiveStrategy,
    ScheduledActivityStrategy,
    create_activity_strategy,
    DEFAULT_ACTIVITY_STRATEGY,
)
from app.simulation.time_utils import get_next_midnight, simulation_time_from_hour


class SimulationStatus(Enum):
    """Possible simulation states."""
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    STOPPED = auto()
    COMPLETED = auto()


@dataclass
class ScooterGroupSpec:
    """Specification for a group of scooters with shared parameters."""
    name: str
    count: int
    color: str = "#22C55E"
    speed: Optional[float] = None
    swap_threshold: Optional[float] = None
    movement_strategy: Optional[Union[MovementStrategyType, MovementStrategy]] = None
    activity_strategy: Optional[Union[ActivityStrategyType, ActivityStrategy]] = None
    # Activity schedule parameters (used when activity_strategy is SCHEDULED)
    activity_start_hour: float = 8.0
    activity_end_hour: float = 20.0
    max_distance_per_day_km: Optional[float] = None
    low_battery_threshold: float = 0.3


@dataclass
class SimulationConfig:
    """Configuration for the simulation."""
    # Grid dimensions
    grid_width: int = 100
    grid_height: int = 100

    # Time configuration
    max_duration_seconds: float = 86400.0  # 24 hours

    # Scale configuration for time-of-day awareness
    meters_per_grid_unit: float = 100.0
    time_scale: float = 60.0  # Real seconds per simulation second

    # Station configuration
    num_stations: int = 5
    slots_per_station: int = 10
    station_charge_rate_kw: float = 1.3
    initial_batteries_per_station: int = 8

    # Scooter configuration
    num_scooters: int = 50
    scooter_speed: float = 0.025  # grid units per second (9 km/h with default scale)
    swap_threshold: float = 0.2  # 20% triggers swap

    # Battery configuration
    battery_capacity_kwh: float = 1.6
    battery_max_charge_rate_kw: float = 1.3
    consumption_rate_kwh_per_unit: float = 0.005  # kWh per grid unit

    # Random seed for reproducibility
    random_seed: Optional[int] = None

    # Station positions (if None, will be auto-placed)
    station_positions: Optional[List[dict]] = None

    # Movement strategy configuration
    # Can be a MovementStrategyType string, a MovementStrategy instance, or None (uses default)
    movement_strategy: Optional[Union[MovementStrategyType, MovementStrategy]] = None

    # Station seeking behavior (if None, uses default greedy behavior)
    station_seeking_behavior: Optional[StationSeekingBehavior] = None

    # Scooter groups (if provided, overrides num_scooters)
    scooter_groups: Optional[List[ScooterGroupSpec]] = None


@dataclass
class SimulationResult:
    """Results from a simulation run."""
    final_state: WorldState
    metrics: dict
    event_count: int
    simulation_time: float
    status: SimulationStatus


class SimulationEngine:
    """
    Main simulation engine that orchestrates the DES.

    Responsibilities:
    - Initialize world state from config
    - Run event loop
    - Support pause/resume/stop
    - Collect and expose metrics
    - Notify observers of state changes
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.metrics = MetricsCollector()

        # Resolve movement strategy
        movement_strategy = self._resolve_movement_strategy(config.movement_strategy)
        station_seeking = config.station_seeking_behavior or GreedyStationSeekingBehavior()

        self.world = WorldState(
            grid_width=config.grid_width,
            grid_height=config.grid_height,
            metrics=self.metrics,  # Pass metrics to world so events can access it
            movement_strategy=movement_strategy,
            station_seeking_behavior=station_seeking,
        )
        # Store time_scale on world for events to access
        self.world.time_scale = config.time_scale
        self.world.meters_per_grid_unit = config.meters_per_grid_unit

        self.scheduler = EventScheduler(
            max_time=config.max_duration_seconds,
            random_seed=config.random_seed
        )
        self.status = SimulationStatus.IDLE
        self._event_count = 0
        self._observers: List[Callable[[WorldState, Any], None]] = []

    def _resolve_movement_strategy(
        self,
        strategy: Optional[Union[MovementStrategyType, MovementStrategy]]
    ) -> MovementStrategy:
        """Resolve strategy configuration to a MovementStrategy instance."""
        if strategy is None:
            return RandomWalkStrategy()
        elif isinstance(strategy, MovementStrategy):
            return strategy
        elif isinstance(strategy, MovementStrategyType):
            return create_movement_strategy(strategy)
        else:
            # Try to parse as string
            try:
                strategy_type = MovementStrategyType(strategy)
                return create_movement_strategy(strategy_type)
            except ValueError:
                raise ValueError(f"Unknown movement strategy: {strategy}")

    def _resolve_activity_strategy(
        self,
        group: ScooterGroupSpec
    ) -> Optional[ActivityStrategy]:
        """Resolve activity strategy for a scooter group."""
        strategy = group.activity_strategy

        if strategy is None:
            return None  # Use default (AlwaysActiveStrategy)
        elif isinstance(strategy, ActivityStrategy):
            return strategy
        elif strategy == ActivityStrategyType.ALWAYS_ACTIVE:
            return AlwaysActiveStrategy()
        elif strategy == ActivityStrategyType.SCHEDULED:
            return ScheduledActivityStrategy(
                activity_start_hour=group.activity_start_hour,
                activity_end_hour=group.activity_end_hour,
                max_distance_per_day_km=group.max_distance_per_day_km,
                low_battery_threshold=group.low_battery_threshold,
                meters_per_grid_unit=self.config.meters_per_grid_unit,
                time_scale=self.config.time_scale
            )
        else:
            # Try to parse as string
            try:
                strategy_type = ActivityStrategyType(strategy)
                return create_activity_strategy(strategy_type)
            except ValueError:
                raise ValueError(f"Unknown activity strategy: {strategy}")

    def initialize(self) -> None:
        """Set up initial world state and events."""
        reset_event_counter()
        self._initialize_stations()
        self._initialize_batteries()
        self._initialize_scooters()
        self._schedule_initial_events()
        self.status = SimulationStatus.IDLE

    def _initialize_stations(self) -> None:
        """Create stations at specified or auto-generated positions."""
        positions = self.config.station_positions

        if positions is None:
            # Auto-place stations in a grid pattern
            positions = self._generate_station_positions()

        for i, pos in enumerate(positions):
            station = Station(
                id=f"station_{i}",
                position=Position(pos["x"], pos["y"]),
                num_slots=self.config.slots_per_station,
                charge_rate_kw=self.config.station_charge_rate_kw
            )
            self.world.stations[station.id] = station

    def _generate_station_positions(self) -> List[dict]:
        """Generate evenly distributed station positions."""
        positions = []
        n = self.config.num_stations

        # Simple grid distribution
        cols = int(n ** 0.5) + 1
        rows = (n + cols - 1) // cols

        x_step = self.config.grid_width // (cols + 1)
        y_step = self.config.grid_height // (rows + 1)

        count = 0
        for row in range(rows):
            for col in range(cols):
                if count >= n:
                    break
                x = x_step * (col + 1)
                y = y_step * (row + 1)
                positions.append({"x": x, "y": y})
                count += 1

        return positions

    def _get_total_scooters(self) -> int:
        """Get total number of scooters from config or groups."""
        if self.config.scooter_groups:
            return sum(g.count for g in self.config.scooter_groups)
        return self.config.num_scooters

    def _initialize_batteries(self) -> None:
        """Create batteries and place them in stations."""
        battery_id = 0

        for station in self.world.stations.values():
            # Place initial batteries in station slots
            for slot_idx in range(min(self.config.initial_batteries_per_station, station.num_slots)):
                battery = Battery(
                    id=f"battery_{battery_id}",
                    capacity_kwh=self.config.battery_capacity_kwh,
                    max_charge_rate_kw=self.config.battery_max_charge_rate_kw,
                    current_charge_kwh=self.config.battery_capacity_kwh,  # Start full
                    location=BatteryLocation.IN_STATION,
                    station_id=station.id,
                    slot_index=slot_idx
                )
                self.world.batteries[battery.id] = battery
                station.slots[slot_idx].battery_id = battery.id
                battery_id += 1

        # Create batteries for scooters
        num_scooters = self._get_total_scooters()
        for i in range(num_scooters):
            battery = Battery(
                id=f"battery_{battery_id}",
                capacity_kwh=self.config.battery_capacity_kwh,
                max_charge_rate_kw=self.config.battery_max_charge_rate_kw,
                current_charge_kwh=self.config.battery_capacity_kwh * 0.8,  # Start at 80%
                location=BatteryLocation.IN_SCOOTER,
                scooter_id=f"scooter_{i}"
            )
            self.world.batteries[battery.id] = battery
            battery_id += 1

    def _initialize_scooters(self) -> None:
        """Create scooters at random positions, optionally from groups."""
        rng = self.scheduler.get_rng()
        num_scooters = self._get_total_scooters()
        battery_idx = len(self.world.batteries) - num_scooters

        if self.config.scooter_groups:
            self._initialize_scooters_from_groups(rng, battery_idx)
        else:
            self._initialize_scooters_default(rng, battery_idx)

    def _initialize_scooters_default(self, rng, battery_idx: int) -> None:
        """Create scooters with default configuration."""
        for i in range(self.config.num_scooters):
            # Random starting position
            x = rng.integers(0, self.config.grid_width)
            y = rng.integers(0, self.config.grid_height)

            scooter = Scooter(
                id=f"scooter_{i}",
                position=Position(x, y),
                battery_id=f"battery_{battery_idx + i}",
                state=ScooterState.MOVING,
                speed=self.config.scooter_speed,
                consumption_rate=self.config.consumption_rate_kwh_per_unit,
                swap_threshold=self.config.swap_threshold
            )
            self.world.scooters[scooter.id] = scooter

    def _initialize_scooters_from_groups(self, rng, battery_idx: int) -> None:
        """Create scooters from group configurations."""
        scooter_idx = 0

        for group_idx, group in enumerate(self.config.scooter_groups):
            # Resolve strategies for this group
            movement_strategy = None
            if group.movement_strategy is not None:
                movement_strategy = self._resolve_movement_strategy(group.movement_strategy)

            activity_strategy = self._resolve_activity_strategy(group)

            # Use group overrides or fall back to defaults
            speed = group.speed if group.speed is not None else self.config.scooter_speed
            swap_threshold = group.swap_threshold if group.swap_threshold is not None else self.config.swap_threshold

            for i in range(group.count):
                # Random starting position
                x = rng.integers(0, self.config.grid_width)
                y = rng.integers(0, self.config.grid_height)

                scooter = Scooter(
                    id=f"scooter_{scooter_idx}",
                    position=Position(x, y),
                    battery_id=f"battery_{battery_idx + scooter_idx}",
                    state=ScooterState.MOVING,
                    speed=speed,
                    consumption_rate=self.config.consumption_rate_kwh_per_unit,
                    swap_threshold=swap_threshold,
                    group_id=f"group_{group_idx}",
                    movement_strategy=movement_strategy,
                    activity_strategy=activity_strategy,
                )
                self.world.scooters[scooter.id] = scooter
                scooter_idx += 1

        # Store group metadata on world for frontend reference
        self.world.scooter_groups = [
            {
                "id": f"group_{i}",
                "name": g.name,
                "color": g.color,
                "count": g.count,
            }
            for i, g in enumerate(self.config.scooter_groups)
        ]

    def _schedule_initial_events(self) -> None:
        """Schedule initial events to start the simulation."""
        from app.simulation.events import DailyResetEvent
        from app.simulation.mechanics import schedule_move_with_activity_check

        # Schedule initial moves for all scooters using pluggable movement strategy
        for scooter in self.world.scooters.values():
            # Notify strategy that scooter is starting (per-scooter takes precedence)
            strategy = scooter.movement_strategy or self.world.movement_strategy
            if strategy:
                strategy.on_scooter_activated(scooter, self.world, self.scheduler)

            # Use activity check to determine if scooter should start active or idle
            event, time = schedule_move_with_activity_check(scooter, self.world, self.scheduler)
            self.scheduler.schedule(event, time)

        # Schedule charging ticks for all stations
        for station in self.world.stations.values():
            event = BatteryChargingTickEvent(station_id=station.id)
            self.scheduler.schedule(event, 60.0)  # First tick at 60 seconds

        # Schedule first daily reset at midnight (if simulation lasts long enough)
        first_midnight = get_next_midnight(0.0, self.config.time_scale)
        if first_midnight < self.config.max_duration_seconds:
            self.scheduler.schedule(DailyResetEvent(day_number=1), first_midnight)

    def step(self) -> bool:
        """
        Execute a single simulation step (process one event).
        Returns True if step was executed, False if simulation is done.
        """
        if self.scheduler.is_empty():
            self.status = SimulationStatus.COMPLETED
            return False

        result = self.scheduler.next_event()
        if result is None:
            return False

        event, time = result

        # Check if we've exceeded max time
        if time > self.config.max_duration_seconds:
            self.status = SimulationStatus.COMPLETED
            return False

        # Advance simulation time
        self.world.current_time = time

        # Process the event
        new_events = event.process(self.world, self.scheduler)
        self._event_count += 1

        # Schedule new events
        for new_event, new_time in new_events:
            self.scheduler.schedule(new_event, new_time)

        # Sample metrics periodically
        self.metrics.sample_metrics(time)

        # Notify observers
        self._notify_observers(event)

        return True

    def run_sync(self) -> SimulationResult:
        """Run the simulation synchronously until completion."""
        self.status = SimulationStatus.RUNNING

        while self.status == SimulationStatus.RUNNING:
            if not self.step():
                break

        return self._build_result()

    async def run_async(
        self,
        speed_multiplier: float = 1.0,
        update_callback: Optional[Callable[[WorldState], None]] = None,
        update_interval: float = 0.1
    ) -> SimulationResult:
        """
        Run the simulation asynchronously with optional real-time updates.

        Args:
            speed_multiplier: How fast to run (1.0 = real-time, 10.0 = 10x speed)
            update_callback: Called periodically with current state
            update_interval: How often to call update_callback (seconds)
        """
        self.status = SimulationStatus.RUNNING
        last_update_time = 0.0
        last_real_time = asyncio.get_event_loop().time()

        while self.status == SimulationStatus.RUNNING:
            if self.scheduler.is_empty():
                self.status = SimulationStatus.COMPLETED
                break

            # Peek at next event time
            next_time = self.scheduler.peek_next_time()
            if next_time is None or next_time > self.config.max_duration_seconds:
                self.status = SimulationStatus.COMPLETED
                break

            # Calculate real-time delay
            time_diff = next_time - self.world.current_time
            real_delay = time_diff / speed_multiplier

            if real_delay > 0.001:  # Only sleep if meaningful
                await asyncio.sleep(min(real_delay, 0.1))

            # Process event
            if not self.step():
                break

            # Periodic updates
            current_real_time = asyncio.get_event_loop().time()
            if update_callback and current_real_time - last_update_time >= update_interval:
                update_callback(self.world)
                last_update_time = current_real_time

            # Allow other tasks to run
            await asyncio.sleep(0)

        return self._build_result()

    def pause(self) -> None:
        """Pause the simulation."""
        if self.status == SimulationStatus.RUNNING:
            self.status = SimulationStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused simulation."""
        if self.status == SimulationStatus.PAUSED:
            self.status = SimulationStatus.RUNNING

    def stop(self) -> None:
        """Stop the simulation."""
        self.status = SimulationStatus.STOPPED

    def reset(self) -> None:
        """Reset the simulation to initial state."""
        self.metrics.reset()

        # Resolve movement strategy (recreate to reset any internal state)
        movement_strategy = self._resolve_movement_strategy(self.config.movement_strategy)
        station_seeking = self.config.station_seeking_behavior or GreedyStationSeekingBehavior()

        self.world = WorldState(
            grid_width=self.config.grid_width,
            grid_height=self.config.grid_height,
            metrics=self.metrics,  # Pass metrics to world so events can access it
            movement_strategy=movement_strategy,
            station_seeking_behavior=station_seeking,
        )
        # Store time_scale on world for events to access
        self.world.time_scale = self.config.time_scale
        self.world.meters_per_grid_unit = self.config.meters_per_grid_unit

        self.scheduler = EventScheduler(
            max_time=self.config.max_duration_seconds,
            random_seed=self.config.random_seed
        )
        self._event_count = 0
        self.initialize()

    def _build_result(self) -> SimulationResult:
        """Compile final results."""
        return SimulationResult(
            final_state=self.world.snapshot(),
            metrics=self.metrics.compile(),
            event_count=self._event_count,
            simulation_time=self.world.current_time,
            status=self.status
        )

    def add_observer(self, observer: Callable[[WorldState, Any], None]) -> None:
        """Register an observer for state changes."""
        self._observers.append(observer)

    def remove_observer(self, observer: Callable[[WorldState, Any], None]) -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify_observers(self, event: Any) -> None:
        """Notify all observers of a state change."""
        for observer in self._observers:
            try:
                observer(self.world, event)
            except Exception as e:
                print(f"Observer error: {e}")

    def get_snapshot(self) -> dict:
        """Get current state as dictionary."""
        return self.world.to_dict()

    def get_metrics(self) -> dict:
        """Get current metrics."""
        return self.metrics.get_current_metrics()

    @property
    def tick(self) -> int:
        """Current event count (as tick proxy)."""
        return self._event_count

    @property
    def is_completed(self) -> bool:
        """Check if simulation is done."""
        return self.status in (SimulationStatus.COMPLETED, SimulationStatus.STOPPED)
