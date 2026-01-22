"""Pydantic schemas for configuration API."""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class MovementStrategyType(str, Enum):
    """Available movement strategy types for scooter behavior."""
    RANDOM_WALK = "random_walk"
    DIRECTED = "directed"


class ActivityStrategyType(str, Enum):
    """Available activity strategy types for scooter scheduling."""
    ALWAYS_ACTIVE = "always_active"
    SCHEDULED = "scheduled"


class PositionSchema(BaseModel):
    """2D position on the grid."""
    x: int = Field(ge=0, description="X coordinate")
    y: int = Field(ge=0, description="Y coordinate")


class GridConfig(BaseModel):
    """Configuration for the simulation grid."""
    width: int = Field(default=100, ge=10, le=1000, description="Grid width")
    height: int = Field(default=100, ge=10, le=1000, description="Grid height")


class ScaleConfig(BaseModel):
    """Scale factors for real-world unit conversion (for display purposes)."""
    meters_per_grid_unit: float = Field(default=100, ge=10, le=1000, description="Meters per grid unit")
    time_scale: float = Field(default=60, ge=1, le=3600, description="Real seconds per simulation second")


class StationConfig(BaseModel):
    """Configuration for a single swap station."""
    position: PositionSchema
    num_slots: int = Field(default=10, ge=1, le=50, description="Number of battery slots")
    initial_batteries: int = Field(default=8, ge=0, description="Initial charged batteries")


class BatterySpec(BaseModel):
    """Battery specification model."""
    capacity_kwh: float = Field(default=1.6, gt=0, description="Battery capacity in kWh")
    charge_rate_kw: float = Field(default=1.3, gt=0, description="Charging rate in kW")
    consumption_rate: float = Field(default=0.005, gt=0, description="Energy consumption per grid unit")


class ScooterConfig(BaseModel):
    """Configuration for scooters in the simulation."""
    count: int = Field(default=50, ge=1, le=10000, description="Number of scooters")
    speed: float = Field(default=0.025, gt=0, le=100, description="Speed in grid units per second")
    swap_threshold: float = Field(default=0.2, ge=0.05, le=0.5, description="Battery level to trigger swap")
    battery_spec: BatterySpec = Field(default_factory=BatterySpec)


class ActivityScheduleConfig(BaseModel):
    """Configuration for time-based scooter activity scheduling."""
    activity_start_hour: float = Field(
        default=8.0,
        ge=0,
        lt=24,
        description="Hour of day when activity starts (0-23.99)"
    )
    activity_end_hour: float = Field(
        default=20.0,
        ge=0,
        lt=24,
        description="Hour of day when activity ends (0-23.99)"
    )
    max_distance_per_day_km: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum distance per day in kilometers (None = unlimited)"
    )
    low_battery_threshold: float = Field(
        default=0.3,
        ge=0.1,
        le=0.9,
        description="Battery level below which to swap before going idle"
    )


class ScooterGroupConfig(BaseModel):
    """Configuration for a group of scooters with shared parameters."""
    name: str = Field(description="Display name for the group")
    count: int = Field(ge=1, le=10000, description="Number of scooters in this group")
    color: str = Field(
        default="#22C55E",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color for visualization"
    )
    speed: Optional[float] = Field(
        default=None,
        gt=0,
        le=100,
        description="Speed in grid units per second (uses default if None)"
    )
    swap_threshold: Optional[float] = Field(
        default=None,
        ge=0.05,
        le=0.5,
        description="Battery level to trigger swap (uses default if None)"
    )
    movement_strategy: Optional[MovementStrategyType] = Field(
        default=None,
        description="Movement strategy (uses default if None)"
    )
    activity_strategy: ActivityStrategyType = Field(
        default=ActivityStrategyType.ALWAYS_ACTIVE,
        description="Activity strategy for this group"
    )
    activity_schedule: Optional[ActivityScheduleConfig] = Field(
        default=None,
        description="Schedule config (required if activity_strategy is 'scheduled')"
    )


class SimulationConfigRequest(BaseModel):
    """Complete simulation configuration request."""
    grid: GridConfig = Field(default_factory=GridConfig)
    scale: ScaleConfig = Field(default_factory=ScaleConfig)
    stations: Optional[List[StationConfig]] = Field(default=None, description="Station configurations")
    num_stations: int = Field(default=5, ge=1, le=50, description="Number of stations (if stations not specified)")
    slots_per_station: int = Field(default=10, ge=1, le=50, description="Slots per station")
    station_charge_rate_kw: float = Field(default=1.3, gt=0, description="Station charge rate")
    initial_batteries_per_station: int = Field(default=8, ge=0, description="Initial batteries per station")
    scooters: ScooterConfig = Field(default_factory=ScooterConfig)
    scooter_groups: Optional[List[ScooterGroupConfig]] = Field(
        default=None,
        description="Scooter groups with distinct parameters. If provided, overrides scooters.count"
    )
    duration_hours: float = Field(default=24.0, gt=0, le=168, description="Simulation duration in hours")
    random_seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    movement_strategy: MovementStrategyType = Field(
        default=MovementStrategyType.RANDOM_WALK,
        description="Movement strategy for scooter behavior (random_walk or directed)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "grid": {"width": 100, "height": 100},
                "scale": {"meters_per_grid_unit": 100, "time_scale": 60},
                "num_stations": 5,
                "slots_per_station": 10,
                "scooters": {
                    "count": 50,
                    "speed": 0.025,
                    "swap_threshold": 0.2,
                    "battery_spec": {
                        "capacity_kwh": 1.6,
                        "charge_rate_kw": 1.3,
                        "consumption_rate": 0.005
                    }
                },
                "scooter_groups": [
                    {
                        "name": "Morning Fleet",
                        "count": 25,
                        "color": "#22C55E",
                        "activity_strategy": "scheduled",
                        "activity_schedule": {
                            "activity_start_hour": 6.0,
                            "activity_end_hour": 14.0,
                            "max_distance_per_day_km": 50.0
                        }
                    },
                    {
                        "name": "Evening Fleet",
                        "count": 25,
                        "color": "#3B82F6",
                        "activity_strategy": "scheduled",
                        "activity_schedule": {
                            "activity_start_hour": 14.0,
                            "activity_end_hour": 22.0,
                            "max_distance_per_day_km": 50.0
                        }
                    }
                ],
                "duration_hours": 24,
                "random_seed": 42,
                "movement_strategy": "random_walk"
            }
        }
    }


class SimulationConfigResponse(BaseModel):
    """Response with current configuration."""
    grid: GridConfig
    scale: ScaleConfig = Field(default_factory=ScaleConfig)
    num_stations: int
    slots_per_station: int
    station_charge_rate_kw: float
    scooters: ScooterConfig
    scooter_groups: Optional[List[ScooterGroupConfig]] = None
    duration_hours: float
    random_seed: Optional[int]
    movement_strategy: MovementStrategyType = MovementStrategyType.RANDOM_WALK
