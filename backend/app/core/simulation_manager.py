"""Singleton manager for simulation state and lifecycle."""

import asyncio
from typing import Optional, Callable, List, Any
from datetime import datetime
import uuid

from app.core.simulation_engine import SimulationEngine, SimulationConfig, SimulationStatus
from app.models.entities import WorldState
from app.simulation.movement_strategies import MovementStrategyType


class SimulationManager:
    """
    Singleton manager for simulation state and lifecycle.

    Handles:
    - Configuration storage
    - Simulation engine lifecycle (start/stop/pause)
    - State access for API endpoints
    - Event broadcasting
    """

    _instance: Optional["SimulationManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._config: Optional[SimulationConfig] = None
        self._engine: Optional[SimulationEngine] = None
        self._task: Optional[asyncio.Task] = None
        self._session_id: Optional[str] = None
        self._start_time: Optional[datetime] = None
        self._speed_multiplier: float = 1.0
        self._observers: List[Callable[[dict], Any]] = []
        self._update_interval: float = 0.1  # 100ms between updates

    @property
    def status(self) -> SimulationStatus:
        if self._engine:
            return self._engine.status
        return SimulationStatus.IDLE

    @property
    def config(self) -> Optional[SimulationConfig]:
        return self._config

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    def set_config(self, config: SimulationConfig) -> None:
        """Set simulation configuration. Only allowed when not running."""
        if self.status == SimulationStatus.RUNNING:
            raise RuntimeError("Cannot change config while simulation is running")

        self._config = config
        self._engine = SimulationEngine(config)
        self._engine.initialize()

    def set_config_from_dict(self, config_dict: dict) -> None:
        """Set configuration from a dictionary."""
        # Parse movement strategy
        strategy_str = config_dict.get("movement_strategy", "random_walk")
        try:
            movement_strategy = MovementStrategyType(strategy_str)
        except ValueError:
            movement_strategy = MovementStrategyType.RANDOM_WALK

        config = SimulationConfig(
            grid_width=config_dict.get("grid", {}).get("width", 100),
            grid_height=config_dict.get("grid", {}).get("height", 100),
            max_duration_seconds=config_dict.get("duration_hours", 24) * 3600,
            num_stations=len(config_dict.get("stations") or []) or config_dict.get("num_stations", 5),
            slots_per_station=config_dict.get("slots_per_station", 10),
            station_charge_rate_kw=config_dict.get("station_charge_rate_kw", 0.5),
            initial_batteries_per_station=config_dict.get("initial_batteries_per_station", 8),
            num_scooters=config_dict.get("scooters", {}).get("count", 50),
            scooter_speed=config_dict.get("scooters", {}).get("speed", 5.0),
            swap_threshold=config_dict.get("scooters", {}).get("swap_threshold", 0.2),
            battery_capacity_kwh=config_dict.get("scooters", {}).get("battery_spec", {}).get("capacity_kwh", 1.5),
            battery_max_charge_rate_kw=config_dict.get("scooters", {}).get("battery_spec", {}).get("charge_rate_kw", 0.5),
            consumption_rate_kwh_per_unit=config_dict.get("scooters", {}).get("battery_spec", {}).get("consumption_rate", 0.001),
            random_seed=config_dict.get("random_seed"),
            station_positions=config_dict.get("stations"),
            movement_strategy=movement_strategy,
        )
        self.set_config(config)

    async def start(self) -> str:
        """Start the simulation. Returns session ID."""
        if self._config is None or self._engine is None:
            raise RuntimeError("No configuration set")

        if self.status == SimulationStatus.RUNNING:
            raise RuntimeError("Simulation already running")

        self._session_id = str(uuid.uuid4())
        self._start_time = datetime.utcnow()

        # Start simulation as background task
        self._task = asyncio.create_task(self._run_simulation())

        return self._session_id

    async def _run_simulation(self) -> None:
        """Main simulation loop running as asyncio task."""
        if not self._engine:
            return

        self._engine.status = SimulationStatus.RUNNING

        try:
            while self._engine.status == SimulationStatus.RUNNING:
                # Process events in batches for efficiency
                events_processed = 0
                batch_start_time = self._engine.world.current_time

                while events_processed < 100:  # Process up to 100 events per batch
                    if not self._engine.step():
                        break
                    events_processed += 1

                    # Check if enough simulation time has passed for an update
                    time_passed = self._engine.world.current_time - batch_start_time
                    if time_passed >= self._speed_multiplier:
                        break

                # Broadcast state update
                await self._broadcast_update()

                # Calculate sleep time based on speed
                sleep_time = self._update_interval / self._speed_multiplier
                await asyncio.sleep(max(0.01, sleep_time))

                # Check for completion
                if self._engine.is_completed:
                    break

        except asyncio.CancelledError:
            self._engine.status = SimulationStatus.STOPPED
        except Exception as e:
            print(f"Simulation error: {e}")
            self._engine.status = SimulationStatus.STOPPED

    async def _broadcast_update(self) -> None:
        """Broadcast state update to all observers."""
        if not self._engine:
            return

        update = {
            "type": "state_update",
            "timestamp": datetime.utcnow().isoformat(),
            "simulation_time": self._engine.world.current_time,
            "tick": self._engine.tick,
            "status": self._engine.status.name,
            **self._engine.get_snapshot(),
            "metrics": self._engine.get_metrics(),
        }

        print(f"Broadcasting to {len(self._observers)} observers, tick={self._engine.tick}")
        for observer in self._observers:
            try:
                await observer(update)
            except Exception as e:
                print(f"Observer error: {e}")

    async def pause(self) -> None:
        """Pause the running simulation."""
        if not self._engine or self._engine.status != SimulationStatus.RUNNING:
            raise RuntimeError("Simulation is not running")

        self._engine.pause()

    async def resume(self) -> None:
        """Resume a paused simulation."""
        if not self._engine or self._engine.status != SimulationStatus.PAUSED:
            raise RuntimeError("Simulation is not paused")

        self._engine.resume()
        self._task = asyncio.create_task(self._run_simulation())

    async def stop(self) -> None:
        """Stop the simulation completely."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        if self._engine:
            self._engine.stop()

    async def reset(self) -> None:
        """Reset simulation to initial state."""
        await self.stop()

        if self._engine:
            self._engine.reset()

    def step(self) -> bool:
        """Execute single simulation step (for debugging)."""
        if not self._engine:
            raise RuntimeError("No simulation engine initialized")

        return self._engine.step()

    def set_speed(self, multiplier: float) -> None:
        """Adjust simulation speed."""
        self._speed_multiplier = max(0.1, min(100.0, multiplier))

    def get_snapshot(self) -> Optional[dict]:
        """Get current simulation state snapshot."""
        if self._engine:
            return {
                "simulation_time": self._engine.world.current_time,
                "tick": self._engine.tick,
                "status": self._engine.status.name,
                **self._engine.get_snapshot(),
            }
        return None

    def get_metrics(self) -> Optional[dict]:
        """Get current metrics."""
        if self._engine:
            return self._engine.get_metrics()
        return None

    def get_metrics_summary(self) -> Optional[dict]:
        """Get full metrics summary."""
        if self._engine:
            return self._engine.metrics.compile()
        return None

    def add_observer(self, observer: Callable[[dict], Any]) -> None:
        """Register an observer for state updates."""
        self._observers.append(observer)

    def remove_observer(self, observer: Callable[[dict], Any]) -> None:
        """Remove an observer."""
        if observer in self._observers:
            self._observers.remove(observer)

    def get_status_info(self) -> dict:
        """Get detailed status information."""
        return {
            "status": self.status.name,
            "session_id": self._session_id,
            "simulation_time": self._engine.world.current_time if self._engine else 0,
            "tick": self._engine.tick if self._engine else 0,
            "speed_multiplier": self._speed_multiplier,
            "start_time": self._start_time.isoformat() if self._start_time else None,
        }


# Dependency for FastAPI
_manager_instance: Optional[SimulationManager] = None


def get_simulation_manager() -> SimulationManager:
    """Get the singleton simulation manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SimulationManager()
    return _manager_instance
