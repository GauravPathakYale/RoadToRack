"""Metrics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.simulation_manager import SimulationManager, get_simulation_manager
from app.models.schemas.metrics import CurrentMetrics, MetricsSummary

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
