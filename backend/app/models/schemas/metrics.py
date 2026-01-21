"""Pydantic schemas for metrics API."""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class CurrentMetrics(BaseModel):
    """Current real-time metrics."""
    total_swaps: int
    total_misses: int
    miss_rate: float
    no_battery_misses: int
    partial_charge_misses: int


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
