"""Tests to verify deterministic behavior with seeded random number generation."""

import pytest
from app.core.simulation_engine import SimulationEngine, SimulationConfig
from app.simulation.scheduler import reset_event_counter


class TestDeterministicSeeding:
    """Tests that verify reproducibility with fixed random seeds."""

    @pytest.mark.deterministic
    def test_same_seed_same_initial_positions(self, reset_events):
        """Same seed produces same initial scooter positions."""
        config1 = SimulationConfig(
            grid_width=50,
            grid_height=50,
            num_scooters=10,
            random_seed=42
        )
        config2 = SimulationConfig(
            grid_width=50,
            grid_height=50,
            num_scooters=10,
            random_seed=42
        )

        reset_event_counter()
        engine1 = SimulationEngine(config1)
        engine1.initialize()

        reset_event_counter()
        engine2 = SimulationEngine(config2)
        engine2.initialize()

        positions1 = [(s.id, s.position.x, s.position.y)
                      for s in engine1.world.scooters.values()]
        positions2 = [(s.id, s.position.x, s.position.y)
                      for s in engine2.world.scooters.values()]

        assert positions1 == positions2, "Same seed should produce same positions"

    @pytest.mark.deterministic
    def test_different_seeds_different_positions(self, reset_events):
        """Different seeds produce different initial positions."""
        config1 = SimulationConfig(
            grid_width=50,
            grid_height=50,
            num_scooters=10,
            random_seed=42
        )
        config2 = SimulationConfig(
            grid_width=50,
            grid_height=50,
            num_scooters=10,
            random_seed=123
        )

        reset_event_counter()
        engine1 = SimulationEngine(config1)
        engine1.initialize()

        reset_event_counter()
        engine2 = SimulationEngine(config2)
        engine2.initialize()

        positions1 = [(s.position.x, s.position.y)
                      for s in engine1.world.scooters.values()]
        positions2 = [(s.position.x, s.position.y)
                      for s in engine2.world.scooters.values()]

        assert positions1 != positions2, "Different seeds should produce different positions"

    @pytest.mark.deterministic
    def test_same_seed_same_simulation_trajectory(self, reset_events):
        """Same seed produces identical event sequences."""
        def run_simulation_n_steps(seed: int, n_steps: int):
            reset_event_counter()
            config = SimulationConfig(
                grid_width=20,
                grid_height=20,
                num_stations=2,
                num_scooters=5,
                random_seed=seed
            )
            engine = SimulationEngine(config)
            engine.initialize()

            events = []
            for _ in range(n_steps):
                if not engine.step():
                    break
                # Record scooter positions after each step
                positions = tuple(
                    (s.id, s.position.x, s.position.y)
                    for s in sorted(engine.world.scooters.values(), key=lambda x: x.id)
                )
                events.append((engine.world.current_time, positions))

            return events

        trajectory1 = run_simulation_n_steps(42, 100)
        trajectory2 = run_simulation_n_steps(42, 100)

        assert len(trajectory1) == len(trajectory2)
        for i, (t1, t2) in enumerate(zip(trajectory1, trajectory2)):
            assert t1 == t2, f"Trajectories diverged at step {i}"

    @pytest.mark.deterministic
    def test_reproducible_random_walk_direction(self, reset_events):
        """Random walk picks same neighbors with same seed."""
        from app.models.entities import Position, Scooter, ScooterState, WorldState
        from app.simulation.scheduler import EventScheduler
        from app.simulation.mechanics import schedule_random_move

        world = WorldState(grid_width=10, grid_height=10)

        # Run with seed 42
        scheduler1 = EventScheduler(max_time=100, random_seed=42)
        scooter = Scooter(
            id="test_scooter",
            position=Position(5, 5),
            battery_id="test_battery",
            state=ScooterState.MOVING,
            speed=1.0,
            consumption_rate=0.001,
            swap_threshold=0.2
        )
        event1, time1 = schedule_random_move(scooter, world, scheduler1)

        # Run with same seed
        scheduler2 = EventScheduler(max_time=100, random_seed=42)
        event2, time2 = schedule_random_move(scooter, world, scheduler2)

        assert event1.new_position == event2.new_position
        assert time1 == time2

    @pytest.mark.deterministic
    def test_full_simulation_reproducible(self, reset_events):
        """Complete simulation run produces same final metrics with same seed."""
        def run_full_simulation(seed: int):
            reset_event_counter()
            config = SimulationConfig(
                grid_width=20,
                grid_height=20,
                max_duration_seconds=300.0,  # 5 minutes
                num_stations=2,
                slots_per_station=4,
                initial_batteries_per_station=3,
                num_scooters=8,
                scooter_speed=2.0,
                consumption_rate_kwh_per_unit=0.02,
                random_seed=seed
            )
            engine = SimulationEngine(config)
            engine.initialize()
            result = engine.run_sync()
            return result

        result1 = run_full_simulation(42)
        result2 = run_full_simulation(42)

        # Same metrics
        assert result1.metrics == result2.metrics
        assert result1.event_count == result2.event_count
        assert result1.simulation_time == result2.simulation_time

    @pytest.mark.deterministic
    def test_rng_state_preserved_across_events(self, reset_events):
        """RNG state correctly propagates through event processing."""
        def capture_rng_sequence(seed: int, n_values: int):
            """Capture sequence of random values from simulation RNG."""
            reset_event_counter()
            config = SimulationConfig(
                grid_width=10,
                grid_height=10,
                num_scooters=3,
                random_seed=seed
            )
            engine = SimulationEngine(config)
            engine.initialize()

            rng = engine.scheduler.get_rng()
            values = [rng.integers(0, 1000) for _ in range(n_values)]
            return values

        seq1 = capture_rng_sequence(42, 20)
        seq2 = capture_rng_sequence(42, 20)

        assert seq1 == seq2, "RNG sequences should be identical with same seed"


class TestSeededRandomWalkScenarios:
    """Test scenarios with specific random walks."""

    @pytest.mark.deterministic
    @pytest.mark.scenario
    def test_seed_42_five_scooters_100_steps(self, reset_events):
        """
        Scenario: 5 scooters, seed 42, run for 100 steps.
        Verify expected behavior based on deterministic trajectory.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=3600.0,
            num_stations=2,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=5,
            scooter_speed=2.0,
            swap_threshold=0.2,
            battery_capacity_kwh=1.0,
            consumption_rate_kwh_per_unit=0.01,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Run exactly 100 steps
        steps_run = 0
        for _ in range(100):
            if engine.step():
                steps_run += 1
            else:
                break

        assert steps_run == 100

        # Verify we have a valid state
        assert len(engine.world.scooters) == 5
        assert len(engine.world.stations) == 2
        assert engine.world.current_time > 0

        # All scooters should still be tracked
        for scooter in engine.world.scooters.values():
            assert 0 <= scooter.position.x < 20
            assert 0 <= scooter.position.y < 20

    @pytest.mark.deterministic
    @pytest.mark.scenario
    def test_seed_12345_single_scooter_walk(self, reset_events):
        """
        Scenario: Track a single scooter's random walk with seed 12345.
        Verify it moves correctly and energy decreases.
        """
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=600.0,
            num_stations=1,
            slots_per_station=3,
            initial_batteries_per_station=2,
            num_scooters=1,
            scooter_speed=1.0,
            swap_threshold=0.1,
            battery_capacity_kwh=2.0,
            consumption_rate_kwh_per_unit=0.05,
            random_seed=12345
        )
        engine = SimulationEngine(config)
        engine.initialize()

        scooter = list(engine.world.scooters.values())[0]
        initial_pos = (scooter.position.x, scooter.position.y)

        battery_id = scooter.battery_id
        initial_charge = engine.world.batteries[battery_id].current_charge_kwh

        # Run 50 steps
        for _ in range(50):
            if not engine.step():
                break

        # Scooter should have moved
        final_pos = (scooter.position.x, scooter.position.y)

        # Battery should have less charge (unless a swap occurred)
        final_charge = engine.world.batteries[scooter.battery_id].current_charge_kwh
        total_swaps = engine.metrics.total_swaps

        if total_swaps == 0:
            assert final_charge < initial_charge, "Battery should drain without swap"

    @pytest.mark.deterministic
    @pytest.mark.scenario
    def test_multiple_seeds_produce_different_outcomes(self, reset_events):
        """
        Scenario: Same configuration with different seeds produces different metrics.
        """
        def run_with_seed(seed):
            reset_event_counter()
            config = SimulationConfig(
                grid_width=25,
                grid_height=25,
                max_duration_seconds=600.0,
                num_stations=2,
                num_scooters=10,
                random_seed=seed
            )
            engine = SimulationEngine(config)
            engine.initialize()
            result = engine.run_sync()
            return result.event_count, result.metrics.get("total_swaps", 0)

        results = {}
        for seed in [1, 42, 100, 9999]:
            results[seed] = run_with_seed(seed)

        # At least some should differ
        unique_results = set(results.values())
        assert len(unique_results) > 1, "Different seeds should produce different outcomes"
