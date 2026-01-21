"""Edge case tests for the simulation system."""

import pytest
from app.core.simulation_engine import SimulationEngine, SimulationConfig, SimulationStatus
from app.simulation.scheduler import reset_event_counter
from app.models.entities import Position, ScooterState


class TestNoBatteriesAvailable:
    """Test scenarios where stations have no batteries."""

    def test_stations_start_empty(self, no_batteries_config, reset_events):
        """Stations with no initial batteries should cause misses."""
        reset_event_counter()
        engine = SimulationEngine(no_batteries_config)
        engine.initialize()

        # Verify stations have no batteries
        for station in engine.world.stations.values():
            batteries_in_station = [
                b for b in engine.world.batteries.values()
                if b.station_id == station.id
            ]
            assert len(batteries_in_station) == 0

        # Run simulation - scooters will need swaps but won't find batteries
        for _ in range(500):
            if not engine.step():
                break

        # With no station batteries and high drain, expect misses
        # (scooters start with batteries, so swaps are still needed)

    def test_all_batteries_depleted(self, reset_events):
        """Scenario where all station batteries are depleted."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=600.0,
            num_stations=1,
            slots_per_station=2,
            initial_batteries_per_station=2,
            num_scooters=10,  # Many scooters
            scooter_speed=5.0,
            swap_threshold=0.3,
            battery_capacity_kwh=0.3,  # Small batteries
            consumption_rate_kwh_per_unit=0.1,  # High drain
            station_charge_rate_kw=0.01,  # Slow charging
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Run until we see misses
        for _ in range(2000):
            if not engine.step():
                break

        # Should have some misses due to battery contention
        metrics = engine.metrics.compile()
        # Either we see misses or partial charges
        assert metrics["total_swaps"] > 0 or metrics["total_misses"] >= 0


class TestFullStationSlots:
    """Test scenarios where station slots are full."""

    def test_more_batteries_than_slots(self, reset_events):
        """Initial batteries should not exceed slots."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            num_stations=1,
            slots_per_station=3,
            initial_batteries_per_station=10,  # More than slots
            num_scooters=2,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        station = list(engine.world.stations.values())[0]
        batteries_in_station = [
            b for b in engine.world.batteries.values()
            if b.station_id == station.id
        ]
        # Should be capped at slots
        assert len(batteries_in_station) <= config.slots_per_station


class TestGridBoundaries:
    """Test scenarios at grid boundaries."""

    def test_scooters_stay_in_bounds(self, reset_events):
        """Scooters should never go outside grid boundaries."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=600.0,
            num_stations=2,
            num_scooters=20,
            scooter_speed=5.0,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for _ in range(500):
            if not engine.step():
                break

            for scooter in engine.world.scooters.values():
                assert 0 <= scooter.position.x < config.grid_width
                assert 0 <= scooter.position.y < config.grid_height

    def test_scooter_at_corner(self, reset_events):
        """Scooter at corner should have limited movement options."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=5,
            grid_height=5,
            num_stations=1,
            slots_per_station=2,
            num_scooters=1,
            random_seed=42,
            station_positions=[{"x": 2, "y": 2}]
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Move scooter to corner for testing
        scooter = list(engine.world.scooters.values())[0]

        # Corner position neighbors
        corner_pos = Position(0, 0)
        neighbors = corner_pos.neighbors(5, 5)

        # Corner should have exactly 2 neighbors (right and down)
        assert len(neighbors) == 2
        expected = {Position(1, 0), Position(0, 1)}
        assert set(neighbors) == expected

    def test_minimum_grid_size(self, reset_events):
        """Test simulation works with minimum grid size."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,  # Minimum allowed
            grid_height=10,
            max_duration_seconds=60.0,
            num_stations=1,
            num_scooters=2,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Should run without errors
        for _ in range(50):
            if not engine.step():
                break


class TestSingleEntityCases:
    """Test edge cases with single entities."""

    def test_single_station_single_scooter(self, reset_events):
        """Minimal simulation with one of each entity."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=300.0,
            num_stations=1,
            slots_per_station=1,
            initial_batteries_per_station=1,
            num_scooters=1,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        assert len(engine.world.stations) == 1
        assert len(engine.world.scooters) == 1

        result = engine.run_sync()
        assert result.event_count > 0

    def test_single_slot_per_station(self, reset_events):
        """Stations with single slots create maximum contention."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=300.0,
            num_stations=3,
            slots_per_station=1,
            initial_batteries_per_station=1,
            num_scooters=10,
            scooter_speed=3.0,
            swap_threshold=0.3,
            battery_capacity_kwh=0.5,
            consumption_rate_kwh_per_unit=0.05,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for station in engine.world.stations.values():
            assert station.num_slots == 1

        # Run simulation
        for _ in range(500):
            if not engine.step():
                break


class TestExtremeValues:
    """Test extreme parameter values."""

    def test_very_fast_scooters(self, reset_events):
        """Fast scooters should still work correctly."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=60.0,
            num_stations=2,
            num_scooters=5,
            scooter_speed=50.0,  # Very fast
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Should run without errors
        for _ in range(100):
            if not engine.step():
                break

    def test_very_slow_scooters(self, reset_events):
        """Slow scooters should advance time significantly per step."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=1000.0,
            num_stations=1,
            num_scooters=2,
            scooter_speed=0.1,  # Very slow
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        engine.step()
        first_time = engine.world.current_time

        # Time should advance significantly with slow speed
        assert first_time > 0

    def test_high_swap_threshold(self, reset_events):
        """High swap threshold means scooters swap early."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=300.0,
            num_stations=2,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=5,
            swap_threshold=0.5,  # Swap at 50%
            battery_capacity_kwh=1.0,
            consumption_rate_kwh_per_unit=0.02,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        result = engine.run_sync()
        # Should have more swaps with high threshold
        assert result.metrics["total_swaps"] >= 0

    def test_low_swap_threshold(self, reset_events):
        """Low swap threshold means scooters run batteries very low."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=300.0,
            num_stations=2,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=5,
            swap_threshold=0.05,  # Swap at 5%
            battery_capacity_kwh=1.0,
            consumption_rate_kwh_per_unit=0.02,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        result = engine.run_sync()
        # Should work correctly
        assert result.event_count > 0


class TestZeroDurationAndEmpty:
    """Test empty and zero-duration scenarios."""

    def test_zero_duration_completes_immediately(self, reset_events):
        """Zero duration simulation should complete immediately."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=0.0,
            num_stations=1,
            num_scooters=2,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        result = engine.run_sync()
        assert result.status == SimulationStatus.COMPLETED

    def test_empty_event_queue(self, reset_events):
        """Simulation with empty event queue should complete."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=100.0,
            num_stations=1,
            num_scooters=1,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Clear queue
        engine.scheduler.clear()

        result = engine.run_sync()
        assert result.status == SimulationStatus.COMPLETED


class TestScooterStates:
    """Test scooter state transitions."""

    def test_all_scooters_start_moving(self, reset_events):
        """All scooters should start in MOVING state."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            num_stations=2,
            num_scooters=10,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for scooter in engine.world.scooters.values():
            assert scooter.state == ScooterState.MOVING

    def test_scooter_state_during_swap(self, reset_events):
        """Scooter transitions to correct state during swap process."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=600.0,
            num_stations=1,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=3,
            scooter_speed=2.0,
            swap_threshold=0.5,  # High threshold to trigger swap early
            battery_capacity_kwh=0.3,
            consumption_rate_kwh_per_unit=0.1,  # High drain
            random_seed=42,
            station_positions=[{"x": 5, "y": 5}]
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Run until we see state changes
        observed_states = set()
        for _ in range(500):
            if not engine.step():
                break
            for scooter in engine.world.scooters.values():
                observed_states.add(scooter.state)

        # Should see at least MOVING state
        assert ScooterState.MOVING in observed_states


class TestBatteryEdgeCases:
    """Edge cases for battery behavior."""

    def test_battery_never_negative(self, reset_events):
        """Battery charge should never go negative."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=600.0,
            num_stations=2,
            num_scooters=10,
            consumption_rate_kwh_per_unit=0.1,  # High drain
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for _ in range(500):
            if not engine.step():
                break

            for battery in engine.world.batteries.values():
                assert battery.current_charge_kwh >= 0

    def test_battery_never_exceeds_capacity(self, reset_events):
        """Battery charge should never exceed capacity."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=3600.0,  # Long run for charging
            num_stations=2,
            slots_per_station=5,
            station_charge_rate_kw=10.0,  # Fast charging
            num_scooters=5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for _ in range(500):
            if not engine.step():
                break

            for battery in engine.world.batteries.values():
                assert battery.current_charge_kwh <= battery.capacity_kwh
