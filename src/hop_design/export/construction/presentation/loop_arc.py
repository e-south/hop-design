"""Circular loop-cap coordinates shared by sequence and schematic drawings."""

from dataclasses import dataclass
from math import atan2, cos, pi, sin, sqrt


@dataclass(frozen=True)
class LoopArc:
    x: float
    top: float
    row_gap: float
    bases: int
    pitch: float

    @property
    def radius(self) -> float:
        return max(self.row_gap / 2, (self.bases + 1) * self.pitch / pi)

    @property
    def center_x(self) -> float:
        return self.x + sqrt(max(0, self.radius**2 - (self.row_gap / 2) ** 2))

    def point(self, offset: float) -> tuple[float, float]:
        """Offset zero and bases + 1 are the two stem junctions."""
        angle = atan2(self.row_gap / 2, self.x - self.center_x)
        theta = -angle + 2 * angle * offset / (self.bases + 1)
        return (
            self.center_x + self.radius * cos(theta),
            self.top + self.row_gap / 2 + self.radius * sin(theta),
        )
