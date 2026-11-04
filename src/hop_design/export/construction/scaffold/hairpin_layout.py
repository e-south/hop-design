"""Shared schematic coordinates; geometry is a drawing convention, not a fold."""

import math
from dataclasses import dataclass

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection


@dataclass(frozen=True)
class HairpinLayout:
    portrait: HairpinPortraitProjection

    @property
    def anchor(self) -> float:
        return max(230.0, self.portrait.stem_primary_span.start.offset * 5.0 + 65)

    @property
    def loop_x(self) -> float:
        p = self.portrait
        return self.anchor + (p.loop_span.start.offset - p.stem_primary_span.start.offset - 1) * 5

    @property
    def radius(self) -> float:
        return 17.0 + self.portrait.loop_nt * 1.2

    def point(self, index: float) -> tuple[float, float]:
        p = self.portrait
        start = p.stem_primary_span.start.offset
        ls, le = p.loop_span.start.offset, p.loop_span.end.offset
        if index < ls:
            return self.anchor + (index - start) * 5, 111.0
        if index >= le:
            return self.anchor + (ls - 1 - start - (index - le)) * 5, 145.0
        theta = -math.pi / 2 + math.pi * (index - ls + 1) / (p.loop_nt + 1)
        return self.loop_x + self.radius * math.cos(theta), 128 + 17 * math.sin(theta)
