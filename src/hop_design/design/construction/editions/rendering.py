"""Current presentation over captured facts; producer and renderer stay distinct."""

import json
from typing import TYPE_CHECKING

from hop_design.export.construction.scaffold.report_pdf import render_report_pdf
from hop_design.export.construction.survey.display_projection import display_projection_files
from hop_design.export.construction.survey.figure import compose_figure, domain_csv
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.serialization import canonical_json_bytes

from ..navigation.render_policy import renderer_identity
from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket

if TYPE_CHECKING:
    from ..intents.base import Source
    from .reader import AtlasEdition


class EditionFigure(SourceBoundConstructionPacket):
    _packet_schema = "hop.atlas-edition-figure/v1"


def edition_figure(
    edition: "AtlasEdition",
    *,
    query: "Source | None" = None,
    selection: "Source | None" = None,
    view: str | None = None,
    stage: str | None = None,
    layout: str | None = None,
    render_policy: str | None = None,
    reference_selection: "Source | None" = None,
    display_axes: tuple[str, ...] | None = None,
) -> SourceBoundConstructionPacket:
    """Resolve the view recipe at the presentation boundary, then draw its packet."""
    from ..navigation.figure_context import figure_context
    from ..navigation.landscape_figure import landscape_figure

    context = figure_context(
        edition, selection, view, stage, layout, render_policy, reference_selection, display_axes
    )
    atlas = context.atlas(edition)
    if context.view in {"families", "similarity"}:
        packet = landscape_figure(
            edition,
            query=query,
            selection=context.selection,
            stage=context.stage,
            layout=context.layout,
            atlas=atlas,
            view=context.view,
            display_axes=context.display_axes,
            color=context.color,
        )
    else:
        if context.view != "parameters" or context.stage != "endpoint" or context.layout != "auto":
            raise ValueError("Choose parameters, or families with its stage and layout.")
        packet = _parameter_figure(
            edition,
            query=query,
            selection=context.selection,
            atlas=atlas,
            display_axes=context.display_axes,
        )
    return context.attach(packet, atlas)


def _parameter_figure(
    edition: "AtlasEdition",
    *,
    query: "Source | None",
    selection: "Source | None",
    atlas: MolecularAtlasPacket | None = None,
    display_axes: tuple[str, ...] | None = None,
) -> EditionFigure:
    selected = None if selection is None else edition._selected(selection)
    if selected is not None and query is None:
        query = selected.query.model_dump(mode="json", by_alias=True)
    choices = edition.query(query)
    if selected is not None and edition.select(
        selected.materialized_realization_id, query=query
    ) != selected.model_dump(mode="json", by_alias=True):
        raise ValueError("Figure query disagrees with the selection.")
    identity = selected.materialized_realization_id if selected else None
    plot = render_survey_plot(choices, selected_identity=identity, display_axes=display_axes)
    files = {
        **display_projection_files(plot),
        "plot.svg": plot,
        "figure.svg": plot,
        "choices.json": canonical_json_bytes(choices),
        "domains.csv": domain_csv(choices),
    }
    selection_value = selected.model_dump(mode="json", by_alias=True) if selected else None
    if selection_value is not None:
        atlas = atlas if atlas is not None else edition.atlas(selection_value)
        captured = dict(atlas._files)
        files.update(
            {
                "selection.json": canonical_json_bytes(selection_value),
                "teaching.svg": captured["teaching.svg"],
                "teaching.json": canonical_json_bytes(json.loads(atlas.json_bytes)["teaching"]),
            }
        )
        files["figure.svg"] = compose_figure(
            captured["overview.svg"], plot, choices, selected_identity=identity
        )
    files["figure.pdf"] = render_report_pdf(
        (files["figure.svg"],), title="HOP captured design choices"
    )
    packet = EditionFigure._create(
        files,
        {
            **choices,
            "selection": selection_value,
            "edition_digest": edition.digest,
            "producer": edition.producer,
            "renderer": renderer_identity(),
        },
        "# Captured molecular choices\n\n"
        "Original molecular evidence; independently identified display renderer.\n",
    )
    object.__setattr__(packet, "_roots", (edition._store.root,))
    return packet
