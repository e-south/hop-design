"""Compose a selected hairpin and landscape from shared molecular drawings."""

import json
from typing import TYPE_CHECKING

from hop_design.export.construction.molecular.printing.teaching import teaching_print_files
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf
from hop_design.export.construction.survey.display_projection import display_projection_files
from hop_design.export.construction.survey.figure import compose_figure, domain_csv
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.serialization import canonical_json_bytes

from ..navigation.figure_context import FigureContext
from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket
from .base import Source

if TYPE_CHECKING:
    from .hairpin_choices import HairpinDesignChoices


class HairpinFigure(SourceBoundConstructionPacket):
    _packet_schema = "hop.hairpin-design-figure-packet/v1"


def hairpin_figure(
    choices: "HairpinDesignChoices",
    query: Source | None,
    selection: Source | None,
    context: FigureContext,
    atlas: MolecularAtlasPacket | None,
) -> SourceBoundConstructionPacket:
    selected = None if selection is None else choices._selected(selection)
    if selected and query is None:
        query = selected["query"]
    result = choices.query(query)
    if selected and choices.select(selected, query=query) != selected:
        raise ValueError("Selection does not satisfy this figure query.")
    plot = render_survey_plot(
        result,
        selected_identity=selected["materialized_realization_id"] if selected else None,
        display_axes=context.display_axes,
    )
    files = {
        **display_projection_files(plot),
        "figure.svg": plot,
        "figure.pdf": render_report_pdf((plot,), title="HOP hairpin choices"),
        "choices.json": canonical_json_bytes(result),
        "domains.csv": domain_csv(result),
    }
    if selected:
        files["selection.json"] = canonical_json_bytes(selected)
        atlas = atlas if atlas is not None else choices.atlas(selected)
        teaching = dict(atlas._files)["teaching.svg"]
        files["teaching.svg"] = teaching
        files.update(teaching_print_files(teaching))
        files["teaching.json"] = canonical_json_bytes(json.loads(atlas.json_bytes)["teaching"])
        files["plot.svg"] = plot
        files["figure.svg"] = compose_figure(
            dict(atlas._files)["overview.svg"],
            plot,
            result,
            selected_identity=selected["materialized_realization_id"],
        )
        files["figure.pdf"] = render_report_pdf((files["figure.svg"],), title="HOP hairpin choices")
    packet = HairpinFigure._create(
        files,
        {**result, "selection": selected},
        "# Complete hairpin choices\n\nEach path is a verified hairpin preparation. "
        "Unobserved values remain unresolved.\n",
    )
    object.__setattr__(packet, "_roots", (choices._pool._root,))
    return context.attach(choices._protect(packet), atlas)
