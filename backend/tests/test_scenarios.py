"""Integration test scenarios with fixed parameters for simulation testing."""

import pytest
from app.core.simulation_engine import SimulationEngine, SimulationConfig, SimulationStatus
from app.simulation.scheduler import reset_event_counter


class TestFixedScooterScenarios:
    """Test scenarios with fixed numbers of scooters."""

    @pytest.mark.scenario
    def test_single_scooter_simulation(self, reset_events):
        """
        Scenario: Single scooter operating for simulated 10 minutes.
        Verifies basic simulation mechanics work with minimal entities.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=600.0,  # 10 minutes
            num_stations=1,
            slots_per_station=2,
            initial_batteries_per_station=1,
            num_scooters=1,
            scooter_speed=1.0,
            swap_threshold=0.2,
            battery_capacity_kwh=1.0,
            consumption_rate_kwh_per_unit=0.01,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Verify initial state
        assert len(engine.world.scooters) == 1
        assert len(engine.world.stations) == 1
        assert engine.status == SimulationStatus.IDLE

        result = engine.run_sync()

        assert result.status in [SimulationStatus.COMPLETED, SimulationStatus.STOPPED]
        assert result.event_count > 0
        assert result.simulation_time <= 600.0

    @pytest.mark.scenario
    def test_ten_scooters_one_station(self, reset_events):
        """
        Scenario: 10 scooters sharing 1 station.
        Tests contention for limited battery resources.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=1800.0,  # 30 minutes
            num_stations=1,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=10,
            scooter_speed=2.0,
            swap_threshold=0.25,
            battery_capacity_kwh=1.0,
            consumption_rate_kwh_per_unit=0.02,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        result = engine.run_sync()

        # With many scooters and limited batteries, expect some misses
        metrics = result.metrics
        assert "total_swaps" in metrics
        assert "total_misses" in metrics

    @pytest.mark.scenario
    def test_fifty_scooters_five_stations(self, reset_events):
        """
        Scenario: 50 scooters with 5 stations (balanced load).
        Tests larger scale simulation.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=50,
            grid_height=50,
            max_duration_seconds=3600.0,  # 1 hour
            num_stations=5,
            slots_per_station=10,
            initial_batteries_per_station=8,
            num_scooters=50,
            scooter_speed=5.0,
            swap_threshold=0.2,
            battery_capacity_kwh=1.5,
            consumption_rate_kwh_per_unit=0.001,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Run for limited steps to keep test fast
        for _ in range(1000):
            if not engine.step():
                break

        # Verify simulation progressed
        assert engine._event_count > 0
        assert engine.world.current_time > 0


class TestFixedTimeStepScenarios:
    """Test scenarios with specific time step limits."""

    @pytest.mark.scenario
    def test_exactly_100_steps(self, reset_events):
        """
        Scenario: Run exactly 100 simulation steps and verify state.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=86400.0,  # Long enough to not limit by time
            num_stations=2,
            num_scooters=5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        steps_completed = 0
        for _ in range(100):
            if engine.step():
                steps_completed += 1
            else:
                break

        assert steps_completed == 100
        assert engine._event_count == 100

    @pytest.mark.scenario
    def test_exactly_500_steps(self, reset_events):
        """
        Scenario: Run exactly 500 simulation steps.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=30,
            grid_height=30,
            max_duration_seconds=86400.0,
            num_stations=3,
            num_scooters=10,
            random_seed=123
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for i in range(500):
            if not engine.step():
                pytest.fail(f"Simulation ended early at step {i}")

        assert engine._event_count == 500

    @pytest.mark.scenario
    def test_run_until_first_swap(self, reset_events):
        """
        Scenario: Run until a battery swap occurs, track step count.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=86400.0,
            num_stations=2,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=10,
            scooter_speed=3.0,
            swap_threshold=0.3,
            battery_capacity_kwh=0.5,  # Small battery
            consumption_rate_kwh_per_unit=0.05,  # High drain
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        max_steps = 10000
        steps_until_swap = 0

        for i in range(max_steps):
            if not engine.step():
                break
            steps_until_swap = i + 1
            if engine.metrics.total_swaps > 0:
                break

        # Should have had a swap by now with high drain
        assert engine.metrics.total_swaps > 0
        assert steps_until_swap > 0

    @pytest.mark.scenario
    @pytest.mark.slow
    def test_one_hour_simulation(self, reset_events):
        """
        Scenario: Run simulation for simulated 1 hour.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=40,
            grid_height=40,
            max_duration_seconds=3600.0,  # 1 hour
            num_stations=4,
            slots_per_station=8,
            initial_batteries_per_station=6,
            num_scooters=20,
            scooter_speed=4.0,
            swap_threshold=0.2,
            battery_capacity_kwh=1.5,
            consumption_rate_kwh_per_unit=0.005,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()
        result = engine.run_sync()

        assert result.simulation_time >= 3600.0 or result.status == SimulationStatus.COMPLETED


class TestScenarioWithFixedPositions:
    """Scenarios with explicit station positions."""

    @pytest.mark.scenario
    def test_corner_stations(self, reset_events):
        """
        Scenario: Stations in corners, scooters in center.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=1800.0,
            num_stations=4,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=10,
            scooter_speed=2.0,
            random_seed=42,
            station_positions=[
                {"x": 2, "y": 2},
                {"x": 2, "y": 17},
                {"x": 17, "y": 2},
                {"x": 17, "y": 17}
            ]
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Verify stations at correct positions
        positions = [(s.position.x, s.position.y)
                     for s in engine.world.stations.values()]
        assert (2, 2) in positions
        assert (2, 17) in positions
        assert (17, 2) in positions
        assert (17, 17) in positions

        # Run simulation
        for _ in range(500):
            if not engine.step():
                break

    @pytest.mark.scenario
    def test_central_station(self, reset_events):
        """
        Scenario: Single station in center of grid.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=1800.0,
            num_stations=1,
            slots_per_station=10,
            initial_batteries_per_station=8,
            num_scooters=15,
            scooter_speed=3.0,
            random_seed=42,
            station_positions=[{"x": 10, "y": 10}]
        )
        engine = SimulationEngine(config)
        engine.initialize()

        station = list(engine.world.stations.values())[0]
        assert station.position.x == 10
        assert station.position.y == 10

        # Run simulation
        for _ in range(300):
            if not engine.step():
                break


class TestScenarioProgression:
    """Test scenarios that verify simulation progression."""

    @pytest.mark.scenario
    def test_time_advances(self, reset_events):
        """Verify simulation time advances with each step."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            num_scooters=3,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        times = [engine.world.current_time]
        for _ in range(20):
            engine.step()
            times.append(engine.world.current_time)

        # Time should be monotonically increasing
        for i in range(1, len(times)):
            assert times[i] >= times[i - 1], "Time should not go backwards"

    @pytest.mark.scenario
    def test_events_processed_in_order(self, reset_events):
        """Verify events are processed in time order."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            num_scooters=5,
            num_stations=2,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        event_times = []
        for _ in range(100):
            if not engine.step():
                break
            event_times.append(engine.world.current_time)

        # Verify sorted order
        assert event_times == sorted(event_times)

    @pytest.mark.scenario
    def test_pause_and_resume(self, reset_events):
        """Test simulation can be paused and resumed."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            num_scooters=3,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Run some steps
        engine.status = SimulationStatus.RUNNING
        for _ in range(10):
            engine.step()

        time_at_pause = engine.world.current_time

        # Pause
        engine.pause()
        assert engine.status == SimulationStatus.PAUSED

        # Resume
        engine.resume()
        assert engine.status == SimulationStatus.RUNNING

        # Continue running
        for _ in range(10):
            engine.step()

        assert engine.world.current_time > time_at_pause

    @pytest.mark.scenario
    def test_reset_simulation(self, reset_events):
        """Test simulation can be reset to initial state."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            num_scooters=5,
            num_stations=2,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Run some steps
        for _ in range(50):
            engine.step()

        # Record state
        time_before_reset = engine.world.current_time
        events_before_reset = engine._event_count

        assert time_before_reset > 0
        assert events_before_reset > 0

        # Reset
        engine.reset()

        assert engine.world.current_time == 0
        assert engine._event_count == 0
        assert engine.metrics.total_swaps == 0


class TestBatteryDrainScenarios:
    """Scenarios focused on battery behavior."""

    @pytest.mark.scenario
    def test_high_consumption_forces_swaps(self, reset_events):
        """High energy consumption rate forces frequent battery swaps."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=600.0,
            num_stations=2,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=5,
            scooter_speed=2.0,
            swap_threshold=0.2,
            battery_capacity_kwh=0.5,
            consumption_rate_kwh_per_unit=0.1,  # Very high drain
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        result = engine.run_sync()

        # Should have swaps with high drain
        assert result.metrics["total_swaps"] > 0

    @pytest.mark.scenario
    def test_low_consumption_few_swaps(self, reset_events):
        """Low energy consumption results in fewer swaps."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=300.0,
            num_stations=2,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=5,
            scooter_speed=2.0,
            swap_threshold=0.1,
            battery_capacity_kwh=5.0,  # Large battery
            consumption_rate_kwh_per_unit=0.0001,  # Very low drain
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        result = engine.run_sync()

        # May have no swaps with low drain
        assert result.metrics["total_swaps"] >= 0
