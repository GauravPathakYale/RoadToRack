"""Simulation control API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.simulation_manager import SimulationManager, get_simulation_manager
from app.models.schemas.simulation import (
    SimulationStatusResponse,
    SimulationStartResponse,
    SimulationControlResponse,
    SpeedAdjustRequest,
    SimulationSnapshot,
)

router = APIRouter(prefix="/simulation", tags=["Simulation Control"])


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Get current simulation status and progress."""
    info = sim_manager.get_status_info()
    return SimulationStatusResponse(**info)


@router.get("/snapshot", response_model=SimulationSnapshot)
async def get_simulation_snapshot(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Get current simulation state snapshot."""
    snapshot = sim_manager.get_snapshot()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No simulation running")
    return SimulationSnapshot(**snapshot)


@router.post("/start", response_model=SimulationStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_simulation(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Start the simulation with current configuration."""
    try:
        session_id = await sim_manager.start()
        return SimulationStartResponse(
            message="Simulation started",
            session_id=session_id,
            status=sim_manager.status.name
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pause", response_model=SimulationControlResponse, status_code=status.HTTP_202_ACCEPTED)
async def pause_simulation(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Pause the running simulation."""
    try:
        await sim_manager.pause()
        return SimulationControlResponse(
            message="Simulation paused",
            status=sim_manager.status.name
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resume", response_model=SimulationControlResponse, status_code=status.HTTP_202_ACCEPTED)
async def resume_simulation(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Resume a paused simulation."""
    try:
        await sim_manager.resume()
        return SimulationControlResponse(
            message="Simulation resumed",
            status=sim_manager.status.name
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop", response_model=SimulationControlResponse, status_code=status.HTTP_202_ACCEPTED)
async def stop_simulation(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Stop the simulation completely."""
    await sim_manager.stop()
    return SimulationControlResponse(
        message="Simulation stopped",
        status=sim_manager.status.name
    )


@router.post("/reset", response_model=SimulationControlResponse, status_code=status.HTTP_202_ACCEPTED)
async def reset_simulation(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Reset simulation to initial state."""
    await sim_manager.reset()
    return SimulationControlResponse(
        message="Simulation reset",
        status=sim_manager.status.name
    )


@router.patch("/speed", response_model=SimulationControlResponse)
async def adjust_speed(
    request: SpeedAdjustRequest,
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Adjust simulation speed multiplier."""
    sim_manager.set_speed(request.speed_multiplier)
    return SimulationControlResponse(
        message=f"Speed adjusted to {request.speed_multiplier}x",
        status=sim_manager.status.name
    )


@router.post("/step", response_model=SimulationControlResponse)
async def single_step(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Execute a single simulation step (for debugging)."""
    try:
        executed = sim_manager.step()
        return SimulationControlResponse(
            message="Step executed" if executed else "No more events",
            status=sim_manager.status.name
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
