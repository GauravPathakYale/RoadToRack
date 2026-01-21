"""Position value object for grid-based simulation."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Position:
    """Immutable 2D position on the grid."""
    x: int
    y: int

    def distance_to(self, other: "Position") -> float:
        """Manhattan distance for grid-based movement."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def neighbors(self, grid_width: int, grid_height: int) -> List["Position"]:
        """Return valid neighboring positions (4-directional)."""
        candidates = [
            Position(self.x + 1, self.y),
            Position(self.x - 1, self.y),
            Position(self.x, self.y + 1),
            Position(self.x, self.y - 1),
        ]
        return [
            p for p in candidates
            if 0 <= p.x < grid_width and 0 <= p.y < grid_height
        ]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        # Convert to native Python int to handle numpy int64
        return {"x": int(self.x), "y": int(self.y)}
