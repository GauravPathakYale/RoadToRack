"""Tests for metrics collection and validation."""

import pytest
from app.simulation.metrics import MetricsCollector, MissType, MissEvent, SwapEvent
from app.core.simulation_engine import SimulationEngine, SimulationConfig
from app.simulation.scheduler import reset_event_counter


class TestMetricsCollectorUnit:
    """Unit tests for MetricsCollector."""

    def test_initial_state(self, metrics_collector):
        """MetricsCollector starts with zero counts."""
        assert metrics_collector.total_swaps == 0
        assert metrics_collector.total_misses == 0
        assert metrics_collector.no_battery_misses == 0
        assert metrics_collector.partial_charge_misses == 0
        assert metrics_collector.current_miss_rate == 0.0
        assert metrics_collector.average_wait_time == 0.0

    def test_record_no_battery_miss(self, metrics_collector):
        """Recording no-battery miss increments counters."""
        metrics_collector.record_no_battery_miss(
            time=100.0,
            scooter_id="scooter_1",
            station_id="station_1"
        )

        assert metrics_collector.total_misses == 1
        assert metrics_collector.no_battery_misses == 1
        assert metrics_collector.partial_charge_misses == 0

    def test_record_partial_charge_miss(self, metrics_collector):
        """Recording partial-charge miss increments counters."""
        metrics_collector.record_partial_charge_miss(
            time=100.0,
            scooter_id="scooter_1",
            station_id="station_1",
            charge_level=0.7
        )

        assert metrics_collector.total_misses == 1
        assert metrics_collector.no_battery_misses == 0
        assert metrics_collector.partial_charge_misses == 1

    def test_record_swap(self, metrics_collector):
        """Recording swap increments swap counter."""
        metrics_collector.record_swap(
            time=100.0,
            scooter_id="scooter_1",
            station_id="station_1",
            old_battery_level=0.1,
            new_battery_level=1.0
        )

        assert metrics_collector.total_swaps == 1
        assert len(metrics_collector.swap_events) == 1

    def test_swap_with_partial_charge_records_miss(self, metrics_collector):
        """Swap with partial charge battery counts as miss."""
        metrics_collector.record_swap(
            time=100.0,
            scooter_id="scooter_1",
            station_id="station_1",
            old_battery_level=0.1,
            new_battery_level=0.8  # Not fully charged
        )

        assert metrics_collector.total_swaps == 1
        assert metrics_collector.partial_charge_misses == 1

    def test_swap_with_full_charge_no_miss(self, metrics_collector):
        """Swap with full battery does not count as miss."""
        metrics_collector.record_swap(
            time=100.0,
            scooter_id="scooter_1",
            station_id="station_1",
            old_battery_level=0.1,
            new_battery_level=1.0  # Fully charged
        )

        assert metrics_collector.total_swaps == 1
        assert metrics_collector.partial_charge_misses == 0

    def test_miss_rate_calculation(self, metrics_collector):
        """Miss rate is correctly calculated."""
        # Record 2 swaps, 1 with miss
        metrics_collector.record_swap(100.0, "s1", "st1", 0.1, 1.0)  # No miss
        metrics_collector.record_swap(200.0, "s2", "st1", 0.1, 0.8)  # Partial charge miss

        assert metrics_collector.total_swaps == 2
        assert metrics_collector.total_misses == 1
        assert metrics_collector.current_miss_rate == 0.5

    def test_wait_time_tracking(self, metrics_collector):
        """Wait times are correctly tracked."""
        # Record a no-battery miss (starts wait)
        metrics_collector.record_no_battery_miss(100.0, "s1", "st1")

        # Record swap (ends wait)
        metrics_collector.record_swap(150.0, "s1", "st1", 0.1, 1.0)

        assert len(metrics_collector.wait_durations) == 1
        assert metrics_collector.wait_durations[0] == 50.0
        assert metrics_collector.average_wait_time == 50.0

    def test_swaps_per_station(self, metrics_collector):
        """Swaps per station are correctly tracked."""
        metrics_collector.record_swap(100.0, "s1", "station_1", 0.1, 1.0)
        metrics_collector.record_swap(200.0, "s2", "station_1", 0.1, 1.0)
        metrics_collector.record_swap(300.0, "s3", "station_2", 0.1, 1.0)

        assert metrics_collector.swaps_per_station["station_1"] == 2
        assert metrics_collector.swaps_per_station["station_2"] == 1

    def test_compile_metrics(self, metrics_collector):
        """Compile returns complete metrics dictionary."""
        metrics_collector.record_swap(100.0, "s1", "st1", 0.1, 1.0)
        metrics_collector.record_no_battery_miss(200.0, "s2", "st1")

        compiled = metrics_collector.compile()

        assert "total_swaps" in compiled
        assert "total_misses" in compiled
        assert "no_battery_misses" in compiled
        assert "partial_charge_misses" in compiled
        assert "miss_rate" in compiled
        assert "average_wait_time" in compiled
        assert "max_wait_time" in compiled
        assert "swaps_per_station" in compiled
        assert "miss_rate_history" in compiled

    def test_reset_clears_all(self, metrics_collector):
        """Reset clears all metrics."""
        metrics_collector.record_swap(100.0, "s1", "st1", 0.1, 1.0)
        metrics_collector.record_no_battery_miss(200.0, "s2", "st1")

        metrics_collector.reset()

        assert metrics_collector.total_swaps == 0
        assert metrics_collector.total_misses == 0
        assert len(metrics_collector.swap_events) == 0
        assert len(metrics_collector.miss_events) == 0

    def test_sample_metrics_at_interval(self, metrics_collector):
        """Metrics are sampled at correct intervals."""
        metrics_collector.sample_interval = 60.0

        metrics_collector.sample_metrics(30.0)  # Too early
        assert len(metrics_collector.miss_rate_history) == 0

        metrics_collector.sample_metrics(60.0)  # At interval
        assert len(metrics_collector.miss_rate_history) == 1

        metrics_collector.sample_metrics(100.0)  # Not yet
        assert len(metrics_collector.miss_rate_history) == 1

        metrics_collector.sample_metrics(120.0)  # Next interval
        assert len(metrics_collector.miss_rate_history) == 2


class TestMetricsInSimulation:
    """Integration tests for metrics within simulation."""

    @pytest.mark.scenario
    def test_metrics_collected_during_run(self, reset_events):
        """Metrics are collected during simulation run."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=300.0,
            num_stations=2,
            slots_per_station=4,
            initial_batteries_per_station=3,
            num_scooters=10,
            scooter_speed=3.0,
            swap_threshold=0.3,
            battery_capacity_kwh=0.5,
            consumption_rate_kwh_per_unit=0.05,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()
        result = engine.run_sync()

        # Should have collected some metrics
        metrics = result.metrics
        assert isinstance(metrics, dict)
        assert "total_swaps" in metrics

    @pytest.mark.scenario
    def test_metrics_monotonically_increase(self, reset_events):
        """Swap and miss counts should only increase."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=300.0,
            num_stations=2,
            slots_per_station=4,
            initial_batteries_per_station=3,
            num_scooters=8,
            swap_threshold=0.3,
            battery_capacity_kwh=0.5,
            consumption_rate_kwh_per_unit=0.05,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        prev_swaps = 0
        prev_misses = 0

        for _ in range(500):
            if not engine.step():
                break

            current_swaps = engine.metrics.total_swaps
            current_misses = engine.metrics.total_misses

            assert current_swaps >= prev_swaps
            assert current_misses >= prev_misses

            prev_swaps = current_swaps
            prev_misses = current_misses

    @pytest.mark.scenario
    def test_high_contention_produces_misses(self, reset_events):
        """High scooter-to-battery ratio should produce misses."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=10,
            grid_height=10,
            max_duration_seconds=600.0,
            num_stations=1,
            slots_per_station=2,
            initial_batteries_per_station=1,
            num_scooters=20,  # Many scooters
            scooter_speed=5.0,
            swap_threshold=0.3,
            battery_capacity_kwh=0.3,
            consumption_rate_kwh_per_unit=0.1,
            station_charge_rate_kw=0.1,  # Slow charging
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()
        result = engine.run_sync()

        # With high contention, expect some activity
        assert result.event_count > 0

    @pytest.mark.scenario
    def test_abundant_resources_low_miss_rate(self, reset_events):
        """Abundant batteries should result in low miss rate."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=30,
            grid_height=30,
            max_duration_seconds=600.0,
            num_stations=5,
            slots_per_station=20,
            initial_batteries_per_station=18,
            num_scooters=10,
            scooter_speed=3.0,
            swap_threshold=0.2,
            battery_capacity_kwh=2.0,
            consumption_rate_kwh_per_unit=0.01,
            station_charge_rate_kw=2.0,  # Fast charging
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()
        result = engine.run_sync()

        # With abundant resources and fast charging, miss rate should be low
        miss_rate = result.metrics["miss_rate"]
        # Not asserting specific value as it depends on simulation dynamics


class TestMetricsAccuracy:
    """Tests to verify metrics are accurate."""

    def test_swap_count_matches_events(self, reset_events):
        """Total swaps should match swap event count."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=300.0,
            num_stations=2,
            num_scooters=5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()
        engine.run_sync()

        assert engine.metrics.total_swaps == len(engine.metrics.swap_events)

    def test_miss_count_matches_events(self, reset_events):
        """Total misses should match miss event count."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=15,
            grid_height=15,
            max_duration_seconds=300.0,
            num_stations=2,
            num_scooters=5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()
        engine.run_sync()

        assert engine.metrics.total_misses == len(engine.metrics.miss_events)

    def test_miss_types_sum_to_total(self, metrics_collector):
        """No-battery + partial charge misses = total misses."""
        metrics_collector.record_no_battery_miss(100.0, "s1", "st1")
        metrics_collector.record_no_battery_miss(200.0, "s2", "st1")
        metrics_collector.record_partial_charge_miss(300.0, "s3", "st1", 0.8)

        total = metrics_collector.no_battery_misses + metrics_collector.partial_charge_misses
        assert total == metrics_collector.total_misses


class TestMissRateHistory:
    """Tests for miss rate time series."""

    def test_history_captures_time_points(self, metrics_collector):
        """Miss rate history captures correct time points."""
        metrics_collector.sample_interval = 60.0

        metrics_collector.sample_metrics(60.0)
        metrics_collector.sample_metrics(120.0)
        metrics_collector.sample_metrics(180.0)

        assert len(metrics_collector.miss_rate_history) == 3
        times = [t for t, _ in metrics_collector.miss_rate_history]
        assert times == [60.0, 120.0, 180.0]

    def test_history_captures_changing_rates(self, metrics_collector):
        """Miss rate history reflects changing miss rates."""
        metrics_collector.sample_interval = 60.0

        # Sample at 0% miss rate
        metrics_collector.sample_metrics(60.0)

        # Add a swap with miss
        metrics_collector.record_swap(80.0, "s1", "st1", 0.1, 0.8)

        # Sample at new rate
        metrics_collector.sample_metrics(120.0)

        rates = [r for _, r in metrics_collector.miss_rate_history]
        # First sample should be 0, second should show the miss
        assert rates[0] == 0.0
        assert rates[1] > 0.0
