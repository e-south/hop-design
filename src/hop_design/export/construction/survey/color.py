"""Exact word emphasis or an edition-wide numeric scale for molecular maps."""

from dataclasses import dataclass
from math import floor
from typing import Any

from hop_design.models.construction.variants.view_color import AtlasColorLens

ACCENT, NEUTRAL = "#216e72", "#c5cecf"
RAMP = ((223, 235, 230), (83, 153, 151), (26, 62, 75))


@dataclass(frozen=True)
class MolecularColors:
    lens: AtlasColorLens
    label: str
    colors: dict[str, str | None]


def _shade(t: float) -> str:
    index = min(1, floor(t * 2))
    fraction = t * 2 - index
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
    if axis is None or axis.get("applicable") is False:
        raise ValueError("Color parameter is not applicable to this endpoint.")
    values = {p["values"].get(lens.key) for p in rows} - {None}
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
        {p["materialized_realization_id"]: palette.get(p["values"].get(lens.key)) for p in rows},
    )
