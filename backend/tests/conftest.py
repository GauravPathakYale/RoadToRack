"""Pytest fixtures for simulation tests."""

import pytest
from typing import List, Dict, Any

from app.core.simulation_engine import SimulationEngine, SimulationConfig
from app.simulation.scheduler import EventScheduler, reset_event_counter
from app.simulation.metrics import MetricsCollector
from app.models.entities import (
    WorldState, Position, Battery, BatteryLocation,
    Station, Scooter, ScooterState
)


@pytest.fixture
def reset_events():
    """Reset event counter before each test for determinism."""
    reset_event_counter()
    yield
    reset_event_counter()


@pytest.fixture
def small_grid_config() -> SimulationConfig:
    """Small grid configuration for fast tests."""
    return SimulationConfig(
        grid_width=20,
        grid_height=20,
        max_duration_seconds=3600.0,  # 1 hour
        num_stations=2,
        slots_per_station=5,
        station_charge_rate_kw=1.0,
        initial_batteries_per_station=4,
        num_scooters=5,
        scooter_speed=2.0,
        swap_threshold=0.2,
        battery_capacity_kwh=1.0,
        battery_max_charge_rate_kw=0.5,
        consumption_rate_kwh_per_unit=0.01,
        random_seed=42
    )


@pytest.fixture
def minimal_config() -> SimulationConfig:
    """Minimal configuration for unit tests."""
    return SimulationConfig(
        grid_width=10,
        grid_height=10,
        max_duration_seconds=600.0,  # 10 minutes
        num_stations=1,
        slots_per_station=3,
        station_charge_rate_kw=1.0,
        initial_batteries_per_station=2,
        num_scooters=2,
        scooter_speed=1.0,
        swap_threshold=0.3,
        battery_capacity_kwh=1.0,
        battery_max_charge_rate_kw=0.5,
        consumption_rate_kwh_per_unit=0.05,
        random_seed=12345
    )


@pytest.fixture
def stress_config() -> SimulationConfig:
    """Configuration for stress testing with many scooters."""
    return SimulationConfig(
        grid_width=50,
        grid_height=50,
        max_duration_seconds=7200.0,  # 2 hours
        num_stations=3,
        slots_per_station=5,
        station_charge_rate_kw=0.5,
        initial_batteries_per_station=3,
        num_scooters=50,
        scooter_speed=5.0,
        swap_threshold=0.2,
        battery_capacity_kwh=1.5,
        battery_max_charge_rate_kw=0.5,
        consumption_rate_kwh_per_unit=0.002,
        random_seed=99999
    )


@pytest.fixture
def no_batteries_config() -> SimulationConfig:
    """Configuration where stations start with no batteries (edge case)."""
    return SimulationConfig(
        grid_width=10,
        grid_height=10,
        max_duration_seconds=300.0,
        num_stations=2,
        slots_per_station=5,
        station_charge_rate_kw=1.0,
        initial_batteries_per_station=0,
        num_scooters=5,
        scooter_speed=2.0,
        swap_threshold=0.2,
        battery_capacity_kwh=1.0,
        battery_max_charge_rate_kw=0.5,
        consumption_rate_kwh_per_unit=0.02,
        random_seed=42
    )


@pytest.fixture
def high_drain_config() -> SimulationConfig:
    """Configuration with high energy drain to force frequent swaps."""
    return SimulationConfig(
        grid_width=15,
        grid_height=15,
        max_duration_seconds=600.0,
        num_stations=2,
        slots_per_station=4,
        station_charge_rate_kw=0.5,
        initial_batteries_per_station=3,
        num_scooters=10,
        scooter_speed=3.0,
        swap_threshold=0.3,
        battery_capacity_kwh=0.5,  # Small batteries
        battery_max_charge_rate_kw=0.5,
        consumption_rate_kwh_per_unit=0.05,  # High drain
        random_seed=42
    )


@pytest.fixture
def fixed_station_positions_config() -> SimulationConfig:
    """Configuration with explicit station positions."""
    return SimulationConfig(
        grid_width=20,
        grid_height=20,
        max_duration_seconds=1800.0,
        num_stations=2,
        slots_per_station=5,
        station_charge_rate_kw=1.0,
        initial_batteries_per_station=4,
        num_scooters=5,
        scooter_speed=2.0,
        swap_threshold=0.2,
        battery_capacity_kwh=1.0,
        battery_max_charge_rate_kw=0.5,
        consumption_rate_kwh_per_unit=0.01,
        random_seed=42,
        station_positions=[{"x": 5, "y": 5}, {"x": 15, "y": 15}]
    )


@pytest.fixture
def engine_with_small_grid(small_grid_config, reset_events) -> SimulationEngine:
    """Initialized simulation engine with small grid."""
    engine = SimulationEngine(small_grid_config)
    engine.initialize()
    return engine


@pytest.fixture
def engine_with_minimal(minimal_config, reset_events) -> SimulationEngine:
    """Initialized simulation engine with minimal config."""
    engine = SimulationEngine(minimal_config)
    engine.initialize()
    return engine


@pytest.fixture
def empty_world() -> WorldState:
    """Empty world state for unit tests."""
    return WorldState(grid_width=10, grid_height=10)


@pytest.fixture
def metrics_collector() -> MetricsCollector:
    """Fresh metrics collector."""
    return MetricsCollector()


@pytest.fixture
def scheduler_seeded() -> EventScheduler:
    """Event scheduler with fixed seed."""
    reset_event_counter()
    return EventScheduler(max_time=3600.0, random_seed=42)
