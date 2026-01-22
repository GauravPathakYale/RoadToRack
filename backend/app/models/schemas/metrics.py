"""Pydantic schemas for metrics API."""

from pydantic import BaseModel
from typing import List, Dict, Tuple


class SwapEventRecord(BaseModel):
    """Record of a swap event."""
    timestamp: float
    scooter_id: str
    station_id: str
    old_battery_level: float
    new_battery_level: float
    was_partial: bool


class CurrentMetrics(BaseModel):
    """Current real-time metrics."""
    total_swaps: int
    total_misses: int
    miss_rate: float
    no_battery_misses: int
    partial_charge_misses: int
    misses_per_station: Dict[str, int] = {}
    swaps_per_station: Dict[str, int] = {}


class StationSwapEvents(BaseModel):
    """Swap events for a single station."""
    station_id: str
    total: int
    offset: int
    limit: int
    sort_by: str
    order: str
    swaps: List[SwapEventRecord] = []


class MetricsSummary(BaseModel):
    """Summary statistics for a simulation run."""
    total_swaps: int
    total_misses: int
    no_battery_misses: int
    partial_charge_misses: int
    miss_rate: float
    no_battery_miss_rate: float
    partial_charge_miss_rate: float
    average_wait_time: float
    max_wait_time: float
    swaps_per_station: Dict[str, int]
    miss_rate_history: List[Tuple[float, float]]
    misses_per_station: Dict[str, int] = {}
    no_battery_misses_per_station: Dict[str, int] = {}
    partial_charge_misses_per_station: Dict[str, int] = {}
