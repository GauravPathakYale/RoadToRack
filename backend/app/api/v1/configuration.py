"""Configuration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.simulation_manager import SimulationManager, get_simulation_manager
from app.core.simulation_engine import SimulationConfig
from app.models.schemas.configuration import (
    SimulationConfigRequest,
    SimulationConfigResponse,
    GridConfig,
    ScaleConfig,
    ScooterConfig,
    BatterySpec,
)

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/", response_model=SimulationConfigResponse)
async def get_configuration(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Get current simulation configuration."""
    config = sim_manager.config
    if not config:
        # Return default config
        config = SimulationConfig()

    return SimulationConfigResponse(
        grid=GridConfig(width=config.grid_width, height=config.grid_height),
        scale=ScaleConfig(),  # Scale is frontend-only, return defaults
        num_stations=config.num_stations,
        slots_per_station=config.slots_per_station,
        station_charge_rate_kw=config.station_charge_rate_kw,
        scooters=ScooterConfig(
            count=config.num_scooters,
            speed=config.scooter_speed,
            swap_threshold=config.swap_threshold,
            battery_spec=BatterySpec(
                capacity_kwh=config.battery_capacity_kwh,
                charge_rate_kw=config.battery_max_charge_rate_kw,
                consumption_rate=config.consumption_rate_kwh_per_unit,
            )
        ),
        duration_hours=config.max_duration_seconds / 3600,
        random_seed=config.random_seed,
    )


@router.put("/")
async def set_configuration(
    request: SimulationConfigRequest,
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Set simulation configuration."""
    try:
        # Convert request to dict for manager
        config_dict = request.model_dump()

        # Convert stations if provided
        if request.stations:
            config_dict["stations"] = [
                {"x": s.position.x, "y": s.position.y}
                for s in request.stations
            ]

        sim_manager.set_config_from_dict(config_dict)

        return {"message": "Configuration updated", "status": "configured"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate")
async def validate_configuration(
    request: SimulationConfigRequest,
):
    """Validate configuration without applying."""
    # Pydantic already validates the request
    # Add any additional validation logic here

    errors = []

    # Check station positions are within grid
    if request.stations:
        for i, station in enumerate(request.stations):
            if station.position.x >= request.grid.width:
                errors.append(f"Station {i} x position exceeds grid width")
            if station.position.y >= request.grid.height:
                errors.append(f"Station {i} y position exceeds grid height")
            if station.initial_batteries > station.num_slots:
                errors.append(f"Station {i} has more initial batteries than slots")

    if errors:
        return {"valid": False, "errors": errors}

    return {"valid": True, "errors": []}
