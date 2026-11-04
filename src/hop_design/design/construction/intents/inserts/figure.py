"""Render the same preservation eligibility returned by the public insert query."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ...packets.atlas import MolecularAtlasPacket
from ...surveys.figure import InterfaceSurveyFigure, figure_files
from ..base import Source
from ..comparisons import source_value
from .selection import native_selection

if TYPE_CHECKING:
    from ..results import InsertDesignChoices


def refined_figure(
    choices: InsertDesignChoices,
    query: Source,
    selection: Source | None,
    *,
    atlas: MolecularAtlasPacket | None = None,
    display_axes: tuple[str, ...] | None = None,
) -> InterfaceSurveyFigure:
    selected = None if selection is None else source_value(selection)
    result = choices.query(query)
    if selected:
        native_selection(choices, selected)
        if selected["query"] != result["query"]:
            raise ValueError("Selection query disagrees with this figure query.")
        if not any(
            p["matches"]
            and p["materialized_realization_id"] == selected["materialized_realization_id"]
            for p in result["paths"]
        ):
            raise ValueError("Selected preparation does not satisfy this figure query.")
    if atlas is None and selected is not None:
        atlas = choices.atlas(selected)
    teaching = (
        None
        if atlas is None
        else (dict(atlas._files)["teaching.svg"], json.loads(atlas.json_bytes)["teaching"])
    )
    packet = InterfaceSurveyFigure._create(
        figure_files(
            result,
            choices._pool.parameter_key_svg_bytes,
            choices._pool.parameter_key(),
            selected,
            teaching=teaching,
            overview=None if atlas is None else dict(atlas._files)["overview.svg"],
            display_axes=display_axes,
        ),
        result,
        "# Complete insert choices\n\n"
        "The highlighted paths satisfy the stated regional preservation.\n",
    )
    object.__setattr__(packet, "_roots", ())
    return choices._protect(packet)
