"""Physical type and page budgets shared by choice and molecular figures.

Overflow requires a continuation panel or page, never smaller nucleotide text.
These are HOP's working publication targets, not a journal-specific requirement.
"""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class PrintContract:
    width_pt: float = 504
    height_pt: float = 720
    sequence_pt: float = 8
    annotation_pt: float = 9
    stage_title_pt: float = 11

    def __post_init__(self) -> None:
        values = (
            self.width_pt,
            self.height_pt,
            self.sequence_pt,
            self.annotation_pt,
            self.stage_title_pt,
        )
        if not all(isfinite(v) and v > 0 for v in values):
            raise ValueError("Print dimensions and type sizes must be finite and positive.")

    def units(self, points: float, *, canvas_width: float) -> float:
        if not all(isfinite(v) and v > 0 for v in (points, canvas_width)):
            raise ValueError("Font size and canvas width must be finite and positive.")
        return points * canvas_width / self.width_pt


PUBLICATION = PrintContract()
