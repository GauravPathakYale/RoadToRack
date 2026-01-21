"""Station entity for the simulation."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, TYPE_CHECKING

from .position import Position

if TYPE_CHECKING:
    from .battery import Battery


@dataclass
class ChargingSlot:
    """A single charging slot in a station."""
    index: int
    battery_id: Optional[str] = None
    is_charging: bool = False


@dataclass
class Station:
    """Battery swap station with multiple charging slots."""
    id: str
    position: Position
    num_slots: int
    charge_rate_kw: float
    slots: List[ChargingSlot] = field(default_factory=list)

    def __post_init__(self):
        """Initialize slots if not provided."""
        if not self.slots:
            self.slots = [ChargingSlot(index=i) for i in range(self.num_slots)]

    @property
    def available_batteries(self) -> int:
        """Count slots with batteries (available for swap)."""
        return sum(1 for slot in self.slots if slot.battery_id is not None)

    @property
    def empty_slots(self) -> int:
        """Count empty slots (can accept depleted batteries)."""
        return sum(1 for slot in self.slots if slot.battery_id is None)

    def get_best_battery_slot(self, batteries: Dict[str, "Battery"]) -> Optional[int]:
        """Find slot index with highest-charged battery."""
        best_slot = None
        best_charge = -1.0

        for slot in self.slots:
            if slot.battery_id is not None and slot.battery_id in batteries:
                battery = batteries[slot.battery_id]
                if battery.charge_level > best_charge:
                    best_charge = battery.charge_level
                    best_slot = slot.index

        return best_slot

    def get_empty_slot(self) -> Optional[int]:
        """Find first empty slot for depositing a battery."""
        for slot in self.slots:
            if slot.battery_id is None:
                return slot.index
        return None

    def get_slot(self, index: int) -> Optional[ChargingSlot]:
        """Get slot by index."""
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def count_full_batteries(self, batteries: Dict[str, "Battery"]) -> int:
        """Count batteries that are fully charged (100%)."""
        count = 0
        for slot in self.slots:
            if slot.battery_id and slot.battery_id in batteries:
                if batteries[slot.battery_id].is_full:
                    count += 1
        return count

    def to_dict(self, batteries: Optional[Dict[str, "Battery"]] = None) -> dict:
        """Convert to dictionary for JSON serialization."""
        slot_info = []
        full_batteries = 0

        for slot in self.slots:
            slot_data = {
                "index": int(slot.index),
                "battery_id": slot.battery_id,
                "is_charging": bool(slot.is_charging),
            }
            if batteries and slot.battery_id and slot.battery_id in batteries:
                battery = batteries[slot.battery_id]
                slot_data["charge_level"] = float(battery.charge_level)
                if battery.is_full:
                    full_batteries += 1
            slot_info.append(slot_data)

        return {
            "id": self.id,
            "position": self.position.to_dict(),
            "num_slots": int(self.num_slots),
            "charge_rate_kw": float(self.charge_rate_kw),
            "available_batteries": int(self.available_batteries),
            "full_batteries": int(full_batteries),
            "empty_slots": int(self.empty_slots),
            "slots": slot_info,
        }
