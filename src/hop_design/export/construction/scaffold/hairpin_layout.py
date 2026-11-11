"""Shared schematic coordinates; geometry is a drawing convention, not a fold."""

from dataclasses import dataclass

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..presentation.loop_arc import LoopArc


@dataclass(frozen=True)
class HairpinLayout:
    portrait: HairpinPortraitProjection

    @property
    def anchor(self) -> float:
        return max(230.0, self.portrait.stem_primary_span.start.offset * 5.0 + 65)

    @property
    def loop_x(self) -> float:
        return self.loop_arc.center_x

    @property
    def radius(self) -> float:
        return self.loop_arc.radius

    @property
    def loop_arc(self) -> LoopArc:
        p = self.portrait
        x = self.anchor + (p.loop_span.start.offset - p.stem_primary_span.start.offset - 1) * 5
        return LoopArc(x, 111, 34, p.loop_nt, 5)

    def point(self, index: float) -> tuple[float, float]:
        p = self.portrait
        start = p.stem_primary_span.start.offset
        ls, le = p.loop_span.start.offset, p.loop_span.end.offset
        if index < ls:
            return self.anchor + (index - start) * 5, 111.0
        if index >= le:
            return self.anchor + (ls - 1 - start - (index - le)) * 5, 145.0
        return self.loop_arc.point(index - ls + 1)
