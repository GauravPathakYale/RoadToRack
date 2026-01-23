"""Metrics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal

from app.core.simulation_manager import SimulationManager, get_simulation_manager
from app.models.schemas.metrics import CurrentMetrics, MetricsSummary, StationSwapEvents

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/current", response_model=CurrentMetrics)
async def get_current_metrics(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Get current real-time metrics."""
    metrics = sim_manager.get_metrics()
    if not metrics:
        return CurrentMetrics(
            total_swaps=0,
            total_misses=0,
            miss_rate=0.0,
            no_battery_misses=0,
            partial_charge_misses=0,
        )
    return CurrentMetrics(**metrics)


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Get aggregated summary statistics."""
    summary = sim_manager.get_metrics_summary()
    if not summary:
        raise HTTPException(status_code=404, detail="No simulation data available")
    return MetricsSummary(**summary)


@router.get("/stations/{station_id}/swaps", response_model=StationSwapEvents)
async def get_station_swaps(
    station_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: Literal["battery", "time"] = Query("battery"),
    order: Literal["asc", "desc"] = Query("asc"),
    since: Optional[float] = Query(None, ge=0),
    sim_manager: SimulationManager = Depends(get_simulation_manager)
):
    """Get swap events for a specific station."""
    swaps = sim_manager.get_station_swaps(
        station_id=station_id,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        since=since,
    )
    if swaps is None:
        raise HTTPException(status_code=404, detail="No station swap data available")
    return StationSwapEvents(**swaps)
