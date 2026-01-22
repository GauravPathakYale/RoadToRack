"""Event types for the discrete event simulation."""

from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING
from abc import ABC, abstractmethod

from app.models.entities import Position, ScooterState, BatteryLocation

if TYPE_CHECKING:
    from app.models.entities import WorldState
    from app.simulation.scheduler import EventScheduler


# Constants
SWAP_DURATION = 30.0  # seconds to complete a battery swap


@dataclass
class Event(ABC):
    """Base class for all simulation events."""

    @abstractmethod
    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        """
        Process this event, mutate world state, return new (event, time) tuples to schedule.
        """
        pass

    @abstractmethod
    def description(self) -> str:
        """Human-readable description for logging."""
        pass


@dataclass
class ScooterMoveEvent(Event):
    """Scooter completes a move to next position."""
    scooter_id: str
    new_position: Position

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        from app.simulation.mechanics import (
            schedule_move_with_activity_check,
            schedule_move_toward_station,
        )

        scooter = world.get_scooter(self.scooter_id)
        if not scooter:
            return []

        battery = world.get_battery(scooter.battery_id)
        if not battery:
            return []

        # Calculate energy consumed for this move
        distance = scooter.position.distance_to(self.new_position)
        energy_consumed = distance * scooter.consumption_rate
        battery.consume_energy(energy_consumed)

        # Track daily distance traveled
        scooter.distance_traveled_today += distance

        # Update scooter position
        scooter.position = self.new_position

        new_events = []

        # Check if battery is low and scooter should head to station
        if scooter.needs_swap(battery.charge_level) and scooter.state == ScooterState.MOVING:
            # Find nearest station
            nearest = world.find_nearest_station(scooter.position)
            if nearest:
                scooter.state = ScooterState.TRAVELING_TO_STATION
                scooter.target_station_id = nearest.id
                scooter.target_position = nearest.position

        # Schedule next move based on state
        if scooter.state == ScooterState.MOVING:
            # Check activity strategy, then schedule move if active
            event, time = schedule_move_with_activity_check(scooter, world, scheduler)
            new_events.append((event, time))

        elif scooter.state == ScooterState.TRAVELING_TO_STATION:
            if scooter.position == scooter.target_position:
                # Arrived at station
                event = ScooterArriveAtStationEvent(
                    scooter_id=self.scooter_id,
                    station_id=scooter.target_station_id
                )
                new_events.append((event, world.current_time))
            else:
                event, time = schedule_move_toward_station(scooter, world, scheduler)
                new_events.append((event, time))

        return new_events

    def description(self) -> str:
        return f"Scooter {self.scooter_id} moved to ({self.new_position.x}, {self.new_position.y})"


@dataclass
class ScooterArriveAtStationEvent(Event):
    """Scooter arrives at a station for battery swap."""
    scooter_id: str
    station_id: str

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        scooter = world.get_scooter(self.scooter_id)
        station = world.get_station(self.station_id)

        if not scooter or not station:
            return []

        new_events = []

        # Check if station has batteries and empty slot
        best_slot = station.get_best_battery_slot(world.batteries)
        empty_slot = station.get_empty_slot()

        if best_slot is not None and empty_slot is not None:
            # Can perform swap
            scooter.state = ScooterState.SWAPPING
            event = BatterySwapEvent(
                scooter_id=self.scooter_id,
                station_id=self.station_id,
                take_from_slot=best_slot,
                deposit_to_slot=empty_slot
            )
            new_events.append((event, world.current_time + SWAP_DURATION))
        else:
            # No battery available - wait
            scooter.state = ScooterState.WAITING_FOR_BATTERY

            # Record no-battery miss
            if world.metrics:
                world.metrics.record_no_battery_miss(
                    time=world.current_time,
                    scooter_id=self.scooter_id,
                    station_id=self.station_id
                )

            # Scooter will be woken up by BatteryFullyChargedEvent

        return new_events

    def description(self) -> str:
        return f"Scooter {self.scooter_id} arrived at station {self.station_id}"


@dataclass
class BatterySwapEvent(Event):
    """Battery swap operation completes."""
    scooter_id: str
    station_id: str
    take_from_slot: int
    deposit_to_slot: int

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        from app.simulation.mechanics import schedule_move_with_activity_check

        scooter = world.get_scooter(self.scooter_id)
        station = world.get_station(self.station_id)

        if not scooter or not station:
            return []

        # Get the batteries involved
        old_battery_id = scooter.battery_id
        take_slot = station.get_slot(self.take_from_slot)
        deposit_slot = station.get_slot(self.deposit_to_slot)

        if not take_slot or not take_slot.battery_id:
            # Battery was taken by another scooter during swap duration
            # Try to find another available battery
            new_best_slot = station.get_best_battery_slot(world.batteries)
            new_empty_slot = station.get_empty_slot()

            if new_best_slot is not None and new_empty_slot is not None:
                # Retry swap with new battery
                event = BatterySwapEvent(
                    scooter_id=self.scooter_id,
                    station_id=self.station_id,
                    take_from_slot=new_best_slot,
                    deposit_to_slot=new_empty_slot
                )
                return [(event, world.current_time + SWAP_DURATION)]
            else:
                # No battery available - put scooter in waiting state
                scooter.state = ScooterState.WAITING_FOR_BATTERY
                if world.metrics:
                    world.metrics.record_no_battery_miss(
                        time=world.current_time,
                        scooter_id=self.scooter_id,
                        station_id=self.station_id
                    )
                return []

        new_battery_id = take_slot.battery_id
        old_battery = world.get_battery(old_battery_id)
        new_battery = world.get_battery(new_battery_id)

        if not old_battery or not new_battery:
            return []

        # Save charge levels for metrics before swap
        old_battery_level = old_battery.charge_level
        new_battery_level = new_battery.charge_level

        # Perform the swap
        # 1. Put old battery in station
        old_battery.location = BatteryLocation.IN_STATION
        old_battery.station_id = self.station_id
        old_battery.slot_index = self.deposit_to_slot
        old_battery.scooter_id = None
        deposit_slot.battery_id = old_battery_id
        deposit_slot.is_charging = True

        # 2. Take new battery from station
        new_battery.location = BatteryLocation.IN_SCOOTER
        new_battery.scooter_id = self.scooter_id
        new_battery.station_id = None
        new_battery.slot_index = None
        take_slot.battery_id = None
        take_slot.is_charging = False

        # 3. Update scooter
        scooter.battery_id = new_battery_id
        scooter.state = ScooterState.MOVING
        scooter.target_station_id = None
        scooter.target_position = None

        # 4. Record swap in metrics
        if world.metrics:
            world.metrics.record_swap(
                time=world.current_time,
                scooter_id=self.scooter_id,
                station_id=self.station_id,
                old_battery_level=old_battery_level,
                new_battery_level=new_battery_level
            )

        new_events = []

        # Schedule charging event for deposited battery
        if not old_battery.is_full:
            charge_time = old_battery.time_to_full_charge(station.charge_rate_kw)
            event = BatteryFullyChargedEvent(
                battery_id=old_battery_id,
                station_id=self.station_id,
                slot_index=self.deposit_to_slot
            )
            new_events.append((event, world.current_time + charge_time))

        # Check if scooter should go idle after swap (pre-idle swap flow)
        if scooter.idle_until is not None:
            # Scooter was sent here via ScooterSwapThenIdleEvent
            wake_up_time = scooter.idle_until
            scooter.idle_until = None  # Clear before going idle (will be set by GoIdleEvent)
            event = ScooterGoIdleEvent(
                scooter_id=self.scooter_id,
                wake_up_time=wake_up_time,
                reason="Pre-idle swap completed"
            )
            new_events.append((event, world.current_time))
        else:
            # Schedule next scooter move using pluggable movement strategy
            # Notify strategy that scooter is reactivated after swap (per-scooter takes precedence)
            strategy = scooter.movement_strategy or world.movement_strategy
            if strategy:
                strategy.on_scooter_activated(scooter, world, scheduler)

            # Check activity strategy, then schedule move if active
            event, time = schedule_move_with_activity_check(scooter, world, scheduler)
            new_events.append((event, time))

        return new_events

    def description(self) -> str:
        return f"Scooter {self.scooter_id} swapped battery at station {self.station_id}"


@dataclass
class BatteryChargingTickEvent(Event):
    """Periodic event to update battery charge levels at a station."""
    station_id: str
    tick_interval: float = 60.0  # seconds between ticks

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        station = world.get_station(self.station_id)
        if not station:
            return []

        new_events = []

        for slot in station.slots:
            if slot.battery_id is not None and slot.is_charging:
                battery = world.get_battery(slot.battery_id)
                if battery and not battery.is_full:
                    # Calculate charge added during this tick
                    # charge_rate_kw * tick_interval_seconds / 3600 = kWh added
                    charge_added = (station.charge_rate_kw * self.tick_interval) / 3600
                    battery.add_charge(charge_added)

        # Schedule next tick if simulation continues
        next_tick_time = world.current_time + self.tick_interval
        if next_tick_time < scheduler.max_time:
            event = BatteryChargingTickEvent(
                station_id=self.station_id,
                tick_interval=self.tick_interval
            )
            new_events.append((event, next_tick_time))

        return new_events

    def description(self) -> str:
        return f"Charging tick at station {self.station_id}"


@dataclass
class BatteryFullyChargedEvent(Event):
    """Battery reaches full charge."""
    battery_id: str
    station_id: str
    slot_index: int

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        battery = world.get_battery(self.battery_id)
        station = world.get_station(self.station_id)

        if not battery or not station:
            return []

        # Ensure battery is full
        battery.current_charge_kwh = battery.capacity_kwh

        slot = station.get_slot(self.slot_index)
        if slot:
            slot.is_charging = False

        new_events = []

        # Check if any scooters are waiting at this station
        for scooter in world.scooters.values():
            if (scooter.state == ScooterState.WAITING_FOR_BATTERY and
                scooter.target_station_id == self.station_id):
                # Wake up the waiting scooter
                empty_slot = station.get_empty_slot()
                if empty_slot is not None:
                    scooter.state = ScooterState.SWAPPING
                    event = BatterySwapEvent(
                        scooter_id=scooter.id,
                        station_id=self.station_id,
                        take_from_slot=self.slot_index,
                        deposit_to_slot=empty_slot
                    )
                    new_events.append((event, world.current_time + SWAP_DURATION))
                    break  # Only one scooter gets this battery

        return new_events

    def description(self) -> str:
        return f"Battery {self.battery_id} fully charged at station {self.station_id}"


@dataclass
class ScooterGoIdleEvent(Event):
    """Scooter transitions to IDLE state."""
    scooter_id: str
    wake_up_time: float
    reason: str

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        scooter = world.get_scooter(self.scooter_id)
        if not scooter:
            return []

        # Transition to IDLE state
        scooter.state = ScooterState.IDLE
        scooter.idle_until = self.wake_up_time

        # Clear navigation state
        scooter.target_station_id = None
        scooter.target_position = None

        # Schedule wake-up event
        return [(ScooterWakeUpEvent(scooter_id=self.scooter_id), self.wake_up_time)]

    def description(self) -> str:
        return f"Scooter {self.scooter_id} going idle: {self.reason}"


@dataclass
class ScooterWakeUpEvent(Event):
    """Scooter wakes from IDLE state."""
    scooter_id: str

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        from app.simulation.mechanics import schedule_move
        from app.simulation.activity_strategies import DEFAULT_ACTIVITY_STRATEGY

        scooter = world.get_scooter(self.scooter_id)
        if not scooter or scooter.state != ScooterState.IDLE:
            return []

        # Get activity strategy
        strategy = scooter.activity_strategy or getattr(world, 'activity_strategy', None) or DEFAULT_ACTIVITY_STRATEGY

        # Verify should wake up (schedule might have been stale)
        if not strategy.should_wake_up(scooter, world, world.current_time):
            # Reschedule wake up for later
            result = strategy.check_activity(scooter, world, scheduler)
            if result.wake_up_time:
                return [(ScooterWakeUpEvent(scooter_id=self.scooter_id), result.wake_up_time)]
            return []

        # Wake up - resume movement
        scooter.state = ScooterState.MOVING
        scooter.idle_until = None

        # Notify movement strategy
        movement_strategy = scooter.movement_strategy or world.movement_strategy
        if movement_strategy:
            movement_strategy.on_scooter_activated(scooter, world, scheduler)

        # Schedule next move
        event, time = schedule_move(scooter, world, scheduler)
        return [(event, time)]

    def description(self) -> str:
        return f"Scooter {self.scooter_id} waking from idle"


@dataclass
class ScooterSwapThenIdleEvent(Event):
    """Scooter needs to swap battery before going idle (pre-idle check)."""
    scooter_id: str
    wake_up_time: float
    reason: str

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        from app.simulation.mechanics import schedule_move_toward_station

        scooter = world.get_scooter(self.scooter_id)
        if not scooter:
            return []

        # Store wake time - will be checked after swap completes
        scooter.idle_until = self.wake_up_time

        # Find nearest station and head there
        nearest = world.find_nearest_station(scooter.position)
        if nearest:
            scooter.state = ScooterState.TRAVELING_TO_STATION
            scooter.target_station_id = nearest.id
            scooter.target_position = nearest.position

            event, time = schedule_move_toward_station(scooter, world, scheduler)
            return [(event, time)]
        else:
            # No station available, just go idle
            return [(ScooterGoIdleEvent(
                scooter_id=self.scooter_id,
                wake_up_time=self.wake_up_time,
                reason=self.reason
            ), world.current_time)]

    def description(self) -> str:
        return f"Scooter {self.scooter_id} swapping then idle: {self.reason}"


@dataclass
class DailyResetEvent(Event):
    """Midnight event to reset daily counters and wake/idle scooters."""
    day_number: int  # The day that just started (0-indexed)

    def process(self, world: "WorldState", scheduler: "EventScheduler") -> List[tuple]:
        from app.simulation.mechanics import schedule_move
        from app.simulation.activity_strategies import DEFAULT_ACTIVITY_STRATEGY
        from app.simulation.time_utils import get_next_midnight

        new_events = []

        for scooter in world.scooters.values():
            # Get activity strategy
            strategy = scooter.activity_strategy or getattr(world, 'activity_strategy', None) or DEFAULT_ACTIVITY_STRATEGY

            # Reset daily counters
            strategy.on_day_reset(scooter, world, self.day_number)

            # Check if idle scooters should wake
            if scooter.state == ScooterState.IDLE:
                if strategy.should_wake_up(scooter, world, world.current_time):
                    scooter.state = ScooterState.MOVING
                    scooter.idle_until = None

                    # Notify movement strategy
                    movement_strategy = scooter.movement_strategy or world.movement_strategy
                    if movement_strategy:
                        movement_strategy.on_scooter_activated(scooter, world, scheduler)

                    event, time = schedule_move(scooter, world, scheduler)
                    new_events.append((event, time))

        # Schedule next daily reset
        time_scale = getattr(world, 'time_scale', 60.0)
        next_midnight = get_next_midnight(world.current_time, time_scale)
        if next_midnight < scheduler.max_time:
            new_events.append((
                DailyResetEvent(day_number=self.day_number + 1),
                next_midnight
            ))

        return new_events

    def description(self) -> str:
        return f"Daily reset for day {self.day_number + 1}"
