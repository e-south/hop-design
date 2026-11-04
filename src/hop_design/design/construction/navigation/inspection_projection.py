"""Internal facade for the local inspector's shared publication projections.

Commands consume this adapter without importing molecular or rendering internals.
Public preview packets and their authority checks remain separate and unchanged.
"""

import json
from dataclasses import asdict
from functools import partial

from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
from hop_design.export.construction.presentation.parameter_labels import (
    LABEL_CATALOG_DIGEST,
    display_parameters,
)
from hop_design.export.construction.survey.comparison_features import comparison_features
from hop_design.export.construction.survey.display_projection import inspector_display_axes
from hop_design.export.construction.survey.distributions import render_choice_distributions
from hop_design.export.construction.survey.figure_layout import figure_layout, teaching_geometry
from hop_design.export.construction.survey.plot import render_survey_plot
from hop_design.export.construction.survey.similarity import landscape_geometry
from hop_design.export.construction.survey.traces import TraceProjection
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..editions.preview_job import preview_job, render_preview_job
from ..packets.atlas import MolecularAtlasPacket
from .features.vocabulary import describe_parameters
from .landscape_source import inspection_landscape
from .local_contrast import explain_choice
from .molecular_groups import molecular_families
from .neighbor_work import NeighborWork
from .neighbors import neighboring_preparations
from .preview import preview_components
from .route_presentation import scene_previews
from .types import ChoiceSource, Record


def inspector_packet(packet: MolecularAtlasPacket) -> MolecularAtlasPacket:
    """Recompose current artwork before writing; captured artwork stays authoritative."""
    summary = json.loads(packet.json_bytes)
    if summary.get("rendering", {}).get("effective") != "current":
        return packet
    if summary.get("inspection_profile") == asdict(INSPECTOR_FIGURE):
        return packet
    files = dict(packet._files)
    files["overview.svg"] = render_teaching_overview(summary, profile=INSPECTOR_FIGURE)
    summary["inspection_profile"] = asdict(INSPECTOR_FIGURE)
    result = type(packet)._create(files, summary, packet.report_text)
    object.__setattr__(result, "_roots", packet._roots)
    return result


def map_index(choices: ChoiceSource, answer: Record) -> Record:
    landscape, digest = inspection_landscape(choices, answer=answer)
    geometry = landscape_geometry(landscape)
    members = {p["materialized_realization_id"]: i for i, p in enumerate(answer["paths"])}
    if set(members) != {p["identity"] for p in geometry["points"]}:
        raise ValueError("Map members disagree with the admitted cohort.")
    return {
        "schema": "hop.inspection-map/v1",
        "digest": sha256_digest(canonical_json_bytes({"landscape": digest, "geometry": geometry})),
        "frame": geometry["frame"],
        "radius": geometry["radius"],
        "points": [[members[p["identity"]], p["x"], p["y"]] for p in geometry["points"]],
        "comparison": {
            "algorithm": landscape.algorithm,
            **comparison_features(landscape.preparations, landscape.basis, tuple(members)),
        },
    }


class _InspectionProjection:
    type Trace = TraceProjection

    profile = sha256_digest(
        canonical_json_bytes({"figure": asdict(INSPECTOR_FIGURE), "labels": LABEL_CATALOG_DIGEST})
    )
    display = staticmethod(display_parameters)
    parameters = staticmethod(describe_parameters)
    display_axes = staticmethod(inspector_display_axes)
    trace = staticmethod(partial(TraceProjection, profile=INSPECTOR_FIGURE))
    layout = staticmethod(partial(figure_layout, profile=INSPECTOR_FIGURE))
    teaching = staticmethod(teaching_geometry)
    preview = staticmethod(partial(preview_components, profile=INSPECTOR_FIGURE))
    preview_job = staticmethod(preview_job)
    render_preview_job = staticmethod(render_preview_job)
    scenes = staticmethod(scene_previews)
    packet = staticmethod(inspector_packet)
    explain = staticmethod(explain_choice)
    neighbor_work = NeighborWork
    neighbors = staticmethod(neighboring_preparations)
    map = staticmethod(map_index)
    families = staticmethod(molecular_families)
    distributions = staticmethod(render_choice_distributions)
    axes = staticmethod(partial(render_survey_plot, include_traces=False, profile=INSPECTOR_FIGURE))
