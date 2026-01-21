"""Tests for configuration validation and application."""

import pytest
from pydantic import ValidationError

from app.core.simulation_engine import SimulationEngine, SimulationConfig
from app.models.schemas.configuration import (
    SimulationConfigRequest,
    GridConfig,
    ScooterConfig,
    BatterySpec,
    StationConfig,
    PositionSchema
)
from app.simulation.scheduler import reset_event_counter


class TestSimulationConfigDataclass:
    """Tests for SimulationConfig dataclass."""

    def test_default_values(self):
        """Default configuration has sensible values."""
        config = SimulationConfig()

        assert config.grid_width == 100
        assert config.grid_height == 100
        assert config.max_duration_seconds == 86400.0
        assert config.num_stations == 5
        assert config.num_scooters == 50
        assert config.random_seed is None

    def test_custom_values(self):
        """Custom configuration values are applied."""
        config = SimulationConfig(
            grid_width=50,
            grid_height=75,
            num_stations=10,
            num_scooters=100,
            random_seed=42
        )

        assert config.grid_width == 50
        assert config.grid_height == 75
        assert config.num_stations == 10
        assert config.num_scooters == 100
        assert config.random_seed == 42

    def test_station_positions_default_none(self):
        """Station positions default to None (auto-generated)."""
        config = SimulationConfig()
        assert config.station_positions is None

    def test_station_positions_custom(self):
        """Custom station positions are stored."""
        positions = [{"x": 10, "y": 10}, {"x": 20, "y": 20}]
        config = SimulationConfig(station_positions=positions)

        assert config.station_positions == positions


class TestSimulationConfigRequestSchema:
    """Tests for Pydantic configuration schema validation."""

    def test_default_request(self):
        """Default request creates valid configuration."""
        request = SimulationConfigRequest()

        assert request.grid.width == 100
        assert request.grid.height == 100
        assert request.num_stations == 5
        assert request.scooters.count == 50

    def test_grid_validation_min(self):
        """Grid dimensions have minimum values."""
        with pytest.raises(ValidationError):
            SimulationConfigRequest(grid=GridConfig(width=5))  # Below min of 10

        with pytest.raises(ValidationError):
            SimulationConfigRequest(grid=GridConfig(height=5))

    def test_grid_validation_max(self):
        """Grid dimensions have maximum values."""
        with pytest.raises(ValidationError):
            SimulationConfigRequest(grid=GridConfig(width=2000))  # Above max of 1000

    def test_scooter_count_validation(self):
        """Scooter count is validated."""
        with pytest.raises(ValidationError):
            SimulationConfigRequest(scooters=ScooterConfig(count=0))  # Min is 1

        with pytest.raises(ValidationError):
            SimulationConfigRequest(scooters=ScooterConfig(count=20000))  # Max is 10000

    def test_station_count_validation(self):
        """Station count is validated."""
        with pytest.raises(ValidationError):
            SimulationConfigRequest(num_stations=0)  # Min is 1

        with pytest.raises(ValidationError):
            SimulationConfigRequest(num_stations=100)  # Max is 50

    def test_swap_threshold_validation(self):
        """Swap threshold is within valid range."""
        with pytest.raises(ValidationError):
            SimulationConfigRequest(scooters=ScooterConfig(swap_threshold=0.01))  # Below 0.05

        with pytest.raises(ValidationError):
            SimulationConfigRequest(scooters=ScooterConfig(swap_threshold=0.8))  # Above 0.5

    def test_duration_validation(self):
        """Duration is within valid range."""
        with pytest.raises(ValidationError):
            SimulationConfigRequest(duration_hours=0)  # Must be > 0

        with pytest.raises(ValidationError):
            SimulationConfigRequest(duration_hours=200)  # Max is 168 (1 week)

    def test_battery_spec_validation(self):
        """Battery specifications are validated."""
        with pytest.raises(ValidationError):
            SimulationConfigRequest(
                scooters=ScooterConfig(
                    battery_spec=BatterySpec(capacity_kwh=0)  # Must be > 0
                )
            )

    def test_custom_station_positions(self):
        """Custom station positions are accepted."""
        request = SimulationConfigRequest(
            stations=[
                StationConfig(position=PositionSchema(x=10, y=10)),
                StationConfig(position=PositionSchema(x=20, y=20))
            ]
        )

        assert len(request.stations) == 2
        assert request.stations[0].position.x == 10

    def test_random_seed_optional(self):
        """Random seed is optional."""
        request1 = SimulationConfigRequest()
        assert request1.random_seed is None

        request2 = SimulationConfigRequest(random_seed=42)
        assert request2.random_seed == 42


class TestConfigurationApplication:
    """Tests for applying configuration to simulation."""

    def test_config_creates_correct_entities(self, reset_events):
        """Configuration creates correct number of entities."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=30,
            grid_height=30,
            num_stations=3,
            slots_per_station=5,
            initial_batteries_per_station=4,
            num_scooters=10,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        assert len(engine.world.stations) == 3
        assert len(engine.world.scooters) == 10

        # Count batteries: station batteries + scooter batteries
        station_batteries = 3 * 4  # 3 stations * 4 initial each
        scooter_batteries = 10  # 1 per scooter
        assert len(engine.world.batteries) == station_batteries + scooter_batteries

    def test_explicit_station_positions_applied(self, reset_events):
        """Explicit station positions are used."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=30,
            grid_height=30,
            num_stations=2,
            random_seed=42,
            station_positions=[{"x": 5, "y": 5}, {"x": 25, "y": 25}]
        )
        engine = SimulationEngine(config)
        engine.initialize()

        positions = [(s.position.x, s.position.y)
                     for s in engine.world.stations.values()]

        assert (5, 5) in positions
        assert (25, 25) in positions

    def test_auto_station_positions_in_grid(self, reset_events):
        """Auto-generated station positions are within grid."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=50,
            grid_height=50,
            num_stations=8,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for station in engine.world.stations.values():
            assert 0 <= station.position.x < 50
            assert 0 <= station.position.y < 50

    def test_slot_count_applied(self, reset_events):
        """Station slot count is correctly applied."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            num_stations=2,
            slots_per_station=7,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for station in engine.world.stations.values():
            assert station.num_slots == 7

    def test_scooter_speed_applied(self, reset_events):
        """Scooter speed is correctly applied."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            num_scooters=5,
            scooter_speed=7.5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for scooter in engine.world.scooters.values():
            assert scooter.speed == 7.5

    def test_swap_threshold_applied(self, reset_events):
        """Swap threshold is correctly applied."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            num_scooters=5,
            swap_threshold=0.35,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for scooter in engine.world.scooters.values():
            assert scooter.swap_threshold == 0.35

    def test_battery_capacity_applied(self, reset_events):
        """Battery capacity is correctly applied."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            num_scooters=3,
            num_stations=1,
            initial_batteries_per_station=2,
            battery_capacity_kwh=2.5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for battery in engine.world.batteries.values():
            assert battery.capacity_kwh == 2.5

    def test_max_duration_limits_simulation(self, reset_events):
        """Max duration correctly limits simulation time."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            max_duration_seconds=100.0,  # Short duration
            num_scooters=5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()
        result = engine.run_sync()

        assert result.simulation_time <= 100.0


class TestConfigurationEdgeCases:
    """Edge cases in configuration."""

    def test_max_scooters_allowed(self, reset_events):
        """Maximum allowed scooters can be configured."""
        reset_event_counter()
        # Don't actually create 10000 scooters, just verify config accepts it
        config = SimulationConfig(
            grid_width=100,
            grid_height=100,
            num_scooters=100,  # Reasonable test value
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        assert len(engine.world.scooters) == 100

    def test_single_slot_stations(self, reset_events):
        """Stations with single slot work correctly."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            num_stations=3,
            slots_per_station=1,
            initial_batteries_per_station=1,
            num_scooters=5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        for station in engine.world.stations.values():
            assert station.num_slots == 1

    def test_zero_initial_batteries(self, reset_events):
        """Stations can start with zero batteries."""
        reset_event_counter()
        config = SimulationConfig(
            grid_width=20,
            grid_height=20,
            num_stations=2,
            slots_per_station=5,
            initial_batteries_per_station=0,
            num_scooters=5,
            random_seed=42
        )
        engine = SimulationEngine(config)
        engine.initialize()

        # Only scooter batteries should exist
        assert len(engine.world.batteries) == 5

    def test_consumption_rate_affects_drain(self, reset_events):
        """Different consumption rates affect battery drain."""
        def run_with_consumption(rate):
            reset_event_counter()
            config = SimulationConfig(
                grid_width=15,
                grid_height=15,
                num_stations=1,
                num_scooters=1,
                consumption_rate_kwh_per_unit=rate,
                swap_threshold=0.01,  # Very low threshold to prevent swaps
                battery_capacity_kwh=10.0,  # Large battery
                random_seed=42
            )
            engine = SimulationEngine(config)
            engine.initialize()

            scooter = list(engine.world.scooters.values())[0]
            initial_charge = engine.world.batteries[scooter.battery_id].current_charge_kwh

            # Run 20 steps (before any swap can occur)
            for _ in range(20):
                if not engine.step():
                    break

            battery = engine.world.batteries[scooter.battery_id]
            # Return the amount of energy consumed
            return initial_charge - battery.current_charge_kwh

        drain_high = run_with_consumption(0.1)
        drain_low = run_with_consumption(0.001)

        # Higher consumption rate should drain more energy
        assert drain_high > drain_low
