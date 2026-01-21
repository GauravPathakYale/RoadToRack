"""Battery entity for the simulation."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class BatteryLocation(Enum):
    """Where the battery is located."""
    IN_SCOOTER = auto()
    IN_STATION = auto()


@dataclass
class Battery:
    """Represents a battery that can be in a scooter or charging at a station."""
    id: str
    capacity_kwh: float
    max_charge_rate_kw: float
    current_charge_kwh: float
    location: BatteryLocation

    # If in station, which station and slot
    station_id: Optional[str] = None
    slot_index: Optional[int] = None

    # If in scooter, which scooter
    scooter_id: Optional[str] = None

    @property
    def charge_level(self) -> float:
        """Return charge as percentage (0.0 to 1.0)."""
        return self.current_charge_kwh / self.capacity_kwh

    @property
    def is_full(self) -> bool:
        """Check if battery is fully charged (within small tolerance)."""
        return self.current_charge_kwh >= self.capacity_kwh - 0.0001

    def time_to_full_charge(self, charge_rate_kw: float) -> float:
        """Calculate seconds needed to fully charge at given rate."""
        remaining = self.capacity_kwh - self.current_charge_kwh
        if remaining <= 0:
            return 0.0
        # Convert kWh / kW = hours, then to seconds
        return (remaining / charge_rate_kw) * 3600

    def add_charge(self, energy_kwh: float) -> None:
        """Add energy to battery, capped at capacity."""
        self.current_charge_kwh = min(
            self.capacity_kwh,
            self.current_charge_kwh + energy_kwh
        )

    def consume_energy(self, energy_kwh: float) -> None:
        """Consume energy from battery, floored at 0."""
        self.current_charge_kwh = max(0.0, self.current_charge_kwh - energy_kwh)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "capacity_kwh": float(self.capacity_kwh),
            "current_charge_kwh": float(self.current_charge_kwh),
            "charge_level": float(self.charge_level),
            "is_full": bool(self.is_full),
            "location": self.location.name,
            "station_id": self.station_id,
            "scooter_id": self.scooter_id,
        }
