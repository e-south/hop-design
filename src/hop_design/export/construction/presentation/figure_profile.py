"""Internal composition budgets; molecular geometry and public intent stay separate."""

from dataclasses import dataclass, replace
from math import ceil, isfinite
from typing import Literal

from .print_contract import PUBLICATION


@dataclass(frozen=True)
class FigureProfile:
    key: str
    width: int = 1200
    axis_font: int = ceil(PUBLICATION.units(PUBLICATION.annotation_pt, canvas_width=1200))
    teaching_font: int = 18
    teaching_base_font: int = 16
    loop_label_below: bool = False
    teaching_trace_gap: int = 12
    key_font: int = 16
    minimum_teaching_slot: int = 360
    teaching_slot_step: int = 120
    heading_columns: int = 9
    stable_teaching_slot: bool = False
    compact_context: bool = False
    single_row: bool = False
    rotated_labels: bool = False
    physical_width_pt: float = 504
    node_padding: int = 4
    minimum_axis_gap: float = 2
    heading_pitch_em: float = 0
    region_strip: Literal["above", "below"] = "above"

    def __post_init__(self) -> None:
        if self.region_strip not in {"above", "below"}:
            raise ValueError("The parameter region strip must be above or below the axes.")


PUBLICATION_FIGURE = FigureProfile("publication/v1")
# The selected detail accompanies a map, so it must also work at column width.
# Seven primary coordinates fit one row; detailed views retain continuation rows.
LANDSCAPE_DETAIL_FIGURE = FigureProfile(
    "landscape-detail/v1",
    width=1800,
    axis_font=28,
    single_row=True,
    heading_columns=10,
    compact_context=True,
    teaching_font=32,
    teaching_base_font=19,
    loop_label_below=True,
    teaching_trace_gap=72,
)
INSPECTOR_FIGURE = FigureProfile(
    "inspector/v1",
    width=1100,
    rotated_labels=True,
    single_row=True,
    axis_font=28,
    compact_context=True,
    teaching_font=32,
    key_font=31,
    minimum_teaching_slot=300,
    teaching_slot_step=60,
    heading_columns=10,
    stable_teaching_slot=True,
    region_strip="below",
    minimum_axis_gap=6,
    heading_pitch_em=1.6,
)


COLUMN_DETAIL_FIGURE = FigureProfile(
    "column-detail/v1",
    width=620,
    axis_font=18,
    teaching_font=32,
    teaching_base_font=19,
    loop_label_below=True,
    compact_context=True,
    single_row=True,
    rotated_labels=True,
    physical_width_pt=246,
    node_padding=2,
    teaching_trace_gap=72,
)


def column_detail_profile(width_pt: float) -> FigureProfile:
    """Explicit physical budget for selected details, independent of scientific axes."""
    if isinstance(width_pt, bool) or not isfinite(width_pt) or not 180 <= width_pt <= 720:
        raise ValueError("Detail width must be 180 to 720 points.")
    return replace(
        COLUMN_DETAIL_FIGURE, width=round(620 * width_pt / 246), physical_width_pt=width_pt
    )
