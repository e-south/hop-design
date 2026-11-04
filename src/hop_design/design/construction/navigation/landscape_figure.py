"""Shared landscape projections for browser and publication exports."""

import json
from typing import Any

from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
from hop_design.export.construction.presentation.figure_profile import (
    LANDSCAPE_DETAIL_FIGURE,
    PUBLICATION_FIGURE,
)
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf
from hop_design.export.construction.survey.color import molecular_colors
from hop_design.export.construction.survey.comparison_features import selected_comparison_features
from hop_design.export.construction.survey.comparison_vector import render_comparison_vector
from hop_design.export.construction.survey.display_projection import display_projection_files
from hop_design.export.construction.survey.distributions import render_choice_distributions
from hop_design.export.construction.survey.families import render_molecular_families
from hop_design.export.construction.survey.figure import compose_figure
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.export.construction.survey.similarity import render_molecular_landscape
from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import canonical_json_bytes

from ..intents.base import Source
from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket
from .guided_sampling import selection_source
from .types import ChoiceSource


class MolecularFamilyFigure(SourceBoundConstructionPacket):
    _packet_schema = "hop.molecular-family-figure/v1"


class MolecularSimilarityFigure(SourceBoundConstructionPacket):
    _packet_schema = "hop.molecular-similarity-figure/v1"


def choice_plot(
    choices: ChoiceSource,
    query: Source | None = None,
    *,
    selected_identity: str | None = None,
    view: str = "parameters",
    stage: str = "endpoint",
    layout: str = "auto",
) -> bytes:
    if view == "similarity":
        if stage != "endpoint" or layout != "auto":
            raise ValueError("Molecular similarity uses its frozen hairpin/interface comparison.")
        result = choices.query(query)
        return render_molecular_landscape(
            choices.landscape(),
            eligible={p["materialized_realization_id"] for p in result["paths"] if p["matches"]},
            selected_identity=selected_identity,
        )
    if view == "distributions":
        if layout != "auto":
            raise ValueError("Context distributions use their recorded numeric coordinates.")
        result = choices.query(query)
        families = choices.families(query=query, stage=stage)
        values = next(
            (
                p["values"]
                for p in result["paths"]
                if p["materialized_realization_id"] == selected_identity
            ),
            None,
        )
        return render_choice_distributions(families["distributions"], selected_values=values)
    if view == "families":
        return render_molecular_families(
            choices.families(query=query, stage=stage),
            selected_identity=selected_identity,
            layout=layout,
        )
    if view != "parameters" or stage != "endpoint" or layout != "auto":
        raise ValueError("Choose parameters, or families with its stage and layout.")
    return render_survey_plot(choices.query(query), selected_identity=selected_identity)


def landscape_figure(
    choices: ChoiceSource,
    *,
    query: Source | None = None,
    selection: Source | None = None,
    stage: str = "endpoint",
    layout: str = "auto",
    atlas: MolecularAtlasPacket | None = None,
    view: str = "families",
    display_axes: tuple[str, ...] | None = None,
    color: dict[str, Any] | None = None,
) -> SourceBoundConstructionPacket:
    from .render_policy import renderer_identity

    selected = None if selection is None else selection_source(choices, selection)
    if selected is not None and query is None:
        query = selected["query"]
    result = choices.query(query)
    if (
        selected is not None
        and choices.select(selected["materialized_realization_id"], query=query) != selected
    ):
        raise ValueError("Family figure query disagrees with its exact selection.")
    identity = selected["materialized_realization_id"] if selected else None
    if view == "similarity":
        if stage != "endpoint" or layout != "auto":
            raise ValueError("Molecular similarity uses its frozen hairpin/interface comparison.")
        landscape = choices.landscape()
        plot = render_molecular_landscape(
            landscape,
            eligible={p["materialized_realization_id"] for p in result["paths"] if p["matches"]},
            selected_identity=identity,
            colors=molecular_colors(result, color) if color is not None else None,
        )
        projection = {"landscape": landscape.model_dump(mode="json", by_alias=True)}
        files = {
            "landscape.json": canonical_json_bytes(landscape),
            "plot.svg": plot,
            "figure.svg": plot,
        }
        if identity is not None:
            features = selected_comparison_features(
                landscape.preparations, landscape.basis, identity
            )
            files["comparison-features.json"] = canonical_json_bytes(features)
            files["comparison-features.svg"] = render_comparison_vector(features)
    elif view == "families":
        families = choices.families(query=query, stage=stage)
        plot = render_molecular_families(families, selected_identity=identity, layout=layout)
        projection = {"families": families}
        files = {
            "families.json": canonical_json_bytes(families),
            "plot.svg": plot,
            "figure.svg": plot,
        }
    else:
        raise ValueError("Choose a molecular family or similarity landscape.")
    selected_values = next(
        (p["values"] for p in result["paths"] if p["materialized_realization_id"] == identity), None
    )
    if view == "families":
        files["distributions.svg"] = render_choice_distributions(
            families["distributions"], selected_values=selected_values
        )
    if selected is not None:
        atlas = atlas if atlas is not None else choices.atlas(selected)
        captured = dict(atlas._files)
        files["teaching.svg"] = captured["teaching.svg"]
        files["teaching.json"] = canonical_json_bytes(json.loads(atlas.json_bytes)["teaching"])
        files["selection.json"] = canonical_json_bytes(selected)
        if view == "similarity" or display_axes is not None:
            profile = LANDSCAPE_DETAIL_FIGURE if view == "similarity" else PUBLICATION_FIGURE
            files["overview.svg"] = (
                render_teaching_overview(json.loads(atlas.json_bytes), profile=profile)
                if view == "similarity"
                else captured["overview.svg"]
            )
            files["trace.svg"] = render_survey_plot(
                result, selected_identity=identity, display_axes=display_axes, profile=profile
            )
            files.update(display_projection_files(files["trace.svg"]))
            files["figure.svg"] = compose_figure(
                files["overview.svg"],
                files["trace.svg"],
                result,
                selected_identity=identity,
                profile=profile,
            )
        else:
            files["figure.svg"] = compose_figure(
                captured["overview.svg"], plot, result, selected_identity=identity
            )
    files["figure.pdf"] = render_report_pdf((files["figure.svg"],), title="HOP molecular choices")
    packet_type = MolecularSimilarityFigure if view == "similarity" else MolecularFamilyFigure
    packet = packet_type._create(
        files,
        {
            **projection,
            "choices": result,
            "selection": selected,
            "renderer": renderer_identity(),
            **(
                {"edition_digest": choices.digest, "producer": getattr(choices, "producer", None)}
                if hasattr(choices, "digest")
                else {}
            ),
        },
        "# Molecular landscape\n\n"
        + (
            "Each point identifies one complete preparation. Coordinates compare declared "
            "molecular "
            "features; small display offsets expose preparations at the same position.\n"
            if view == "similarity"
            else "Marks identify exact molecular products; "
            "preparation membership remains explicit.\n"
        ),
    )
    object.__setattr__(packet, "_roots", (ProtectedRoot.capture(choices._directory),))
    return packet
