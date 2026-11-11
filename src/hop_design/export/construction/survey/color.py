"""Exact word emphasis or an edition-wide numeric scale for molecular maps."""

from dataclasses import dataclass
from math import floor
from typing import Any

from hop_design.models.construction.variants.view_color import AtlasColorLens

from ..presentation.palette import BASAL, NUMERIC_BLUE

ACCENT, NEUTRAL = BASAL, "#8D99A5"
RAMP = tuple(tuple(int(color[i : i + 2], 16) for i in (1, 3, 5)) for color in NUMERIC_BLUE)


@dataclass(frozen=True)
class MolecularColors:
    lens: AtlasColorLens
    label: str
    colors: dict[str, str | None]


def _shade(t: float) -> str:
    last = len(RAMP) - 1
    index = min(last - 1, floor(t * last))
    fraction = t * last - index
    return "#" + "".join(
        f"{floor(v + (RAMP[index + 1][i] - v) * fraction + 0.5):02x}"
        for i, v in enumerate(RAMP[index])
    )


def molecular_colors(answer: dict[str, Any], raw: dict[str, Any]) -> MolecularColors:
    """Use all recorded rows; eligibility never rescales a color or changes a word."""
    lens = AtlasColorLens.model_validate(raw)
    rows = answer["paths"]
    if lens.key == "none":
        return MolecularColors(
            lens, "No grouping", {p["materialized_realization_id"]: ACCENT for p in rows}
        )
    axis = next((a for a in answer["axes"] if a["key"] == lens.key), None)
    if lens.key == "max_end_gap":
        sides = [
            next((a for a in answer["axes"] if a["key"] == key), None)
            for key in ("left_gap", "right_gap")
        ]
        if any(side is None or side.get("applicable") is False for side in sides):
            raise ValueError("Larger end gap is not applicable to this endpoint.")
        axis = {"label": "Larger end gap", "unit": "bp"}

    def value(row):
        return lens.value_in(row["values"])

    if axis is None or axis.get("applicable") is False:
        raise ValueError("Color parameter is not applicable to this endpoint.")
    values = {value(p) for p in rows} - {None}
    if not values or (lens.word is not None and lens.word not in values):
        raise ValueError("Color view has no matching value in this recorded pool.")
    if lens.word is not None:
        palette = {v: ACCENT if v == lens.word else NEUTRAL for v in values}
        label = f"{axis['label']} · {lens.word}; other words pale"
    else:
        lo, hi = min(values), max(values)
        palette = {v: ACCENT if lo == hi else _shade((v - lo) / (hi - lo)) for v in values}
        measure = f"{lo}" if lo == hi else f"{lo}\u2013{hi}"
        label = f"{axis['label']} · {measure} {axis['unit']}"
        label += "; constant" if lo == hi else "; pale → dark"
    return MolecularColors(
        lens,
        label,
        {p["materialized_realization_id"]: palette.get(value(p)) for p in rows},
    )
