"""Pydantic schemas for simulation API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SimulationStatusResponse(BaseModel):
    """Response for simulation status endpoint."""
    status: str
    session_id: Optional[str]
    simulation_time: float
    tick: int
    speed_multiplier: float
    start_time: Optional[str]


class SimulationStartResponse(BaseModel):
    """Response when starting simulation."""
    message: str
    session_id: str
    status: str


class SimulationControlResponse(BaseModel):
    """Response for simulation control actions."""
    message: str
    status: str


class SpeedAdjustRequest(BaseModel):
    """Request to adjust simulation speed."""
    speed_multiplier: float = Field(ge=0.1, le=100.0, description="Speed multiplier")


class ScooterStateSchema(BaseModel):
    """Current state of a scooter."""
    id: str
    position: Dict[str, int]
    battery_id: str
    battery_level: float
    state: str
    target_station_id: Optional[str]


class StationStateSchema(BaseModel):
    """Current state of a station."""
    id: str
    position: Dict[str, int]
    num_slots: int
    available_batteries: int
    empty_slots: int


class SimulationSnapshot(BaseModel):
    """Complete snapshot of simulation state."""
    simulation_time: float
    tick: int
    status: str
    grid_width: int
    grid_height: int
    scooters: List[Dict[str, Any]]
    stations: List[Dict[str, Any]]
