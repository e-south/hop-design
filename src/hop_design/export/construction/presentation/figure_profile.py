"""Internal composition budgets; molecular geometry and public intent stay separate."""

from dataclasses import dataclass
from math import ceil

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
    width=1800,
    single_row=True,
    axis_font=28,
    compact_context=True,
    teaching_font=32,
    key_font=31,
    minimum_teaching_slot=300,
    teaching_slot_step=60,
    heading_columns=10,
    stable_teaching_slot=True,
)
