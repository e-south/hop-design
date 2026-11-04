"""Detached single-preparation jobs; cohort admission stays in the parent."""

import json
from dataclasses import dataclass
from typing import cast

from hop_design.export.construction.molecular.assembly.composition import RoutePresentation
from hop_design.export.construction.molecular.teaching_overview import render_projected_teaching
from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.atlas import MolecularScenes
from hop_design.models.construction.variants.similarity import MolecularDescriptor
from hop_design.serialization import canonical_json_bytes

from ..navigation.route_presentation import projected_scene_previews, validate_scene_request
from ..navigation.types import ChoiceSource, Record
from ..projections.atlas import project_molecular_atlas
from .authority import check_descriptor
from .compact_projection import _projection_context, _teaching_summary, teaching_projection
from .descriptors import descriptor_index
from .materials import member_materials, route_record_from_materials
from .reader import AtlasEdition


@dataclass(frozen=True)
class PreviewJob:
    identity: str
    route: bytes
    descriptor: bytes
    context: bytes
    producer: bytes
    edition_digest: str
    phases: tuple[str, ...] | None = None
    presentation: str = "complete"


def preview_job(
    choices: ChoiceSource,
    identity: str,
    answer: Record,
    *,
    render_policy: str = "captured",
    phases: tuple[str, ...] | None = None,
    presentation: str = "complete",
) -> PreviewJob | None:
    if render_policy not in {"captured", "current"}:
        raise ValueError("Choose captured or current render policy.")
    if phases is not None:
        validate_scene_request(phases, presentation, render_policy)
    if not isinstance(choices, AtlasEdition) or not choices._store.compact:
        return None  # Live discovery and captured artwork retain their existing paths.
    if not any(p["materialized_realization_id"] == identity for p in answer["paths"]):
        raise ValueError("Preview must name a preparation in the recorded pool.")
    path, _ = _projection_context(choices, identity, answer)
    context: Record = {
        **{k: answer[k] for k in ("snapshot_digest", "axes", "context", "coverage") if k in answer},
        "paths": [path],
    }
    # These reads check bytes on every cache miss. Never send the cohort graph or
    # a live edition object to the worker, and never use file mtimes as authority.
    return PreviewJob(
        identity=identity,
        route=route_record_from_materials(member_materials(choices, identity), identity),
        descriptor=descriptor_index(choices).get(identity).model_dump_json().encode(),
        context=canonical_json_bytes(context),
        producer=canonical_json_bytes(choices.producer),
        edition_digest=choices.digest,
        phases=phases,
        presentation=presentation,
    )


def render_preview_job(job: PreviewJob) -> tuple[bytes, Record]:
    if job.phases is not None:
        validate_scene_request(job.phases, job.presentation, "current")
    route = MaterializedConstructionRealization.model_validate_json(job.route)
    check_descriptor(route, MolecularDescriptor.model_validate_json(job.descriptor))
    answer = json.loads(job.context)
    path = answer["paths"][0]
    if (
        route.materialized_realization_id != job.identity
        or path["materialized_realization_id"] != job.identity
    ):
        raise ValueError("Preview job disagrees with the selected molecular authority.")
    names = {
        node["value"]: node["label"]
        for axis in answer["axes"]
        if axis["key"].endswith("method")
        for node in axis["nodes"]
    }
    scenes: Record = {}
    atlas: MolecularScenes
    if job.phases is not None:
        atlas = project_molecular_atlas(route, enzyme_names=names)
        summary = _teaching_summary(
            route,
            answer,
            atlas,
            path,
            producer=json.loads(job.producer),
            edition_digest=job.edition_digest,
        )
        drawings, metadata = projected_scene_previews(
            atlas,
            job.identity,
            answer,
            summary,
            phases=job.phases,
            presentation=cast(RoutePresentation, job.presentation),
        )
        scenes = {"route_drawings": drawings, "route_scenes": metadata}
    else:
        atlas, summary = teaching_projection(
            route,
            answer,
            path,
            names,
            producer=json.loads(job.producer),
            edition_digest=job.edition_digest,
        )
    overview = render_projected_teaching(
        atlas, summary["teaching"], summary["parameter_locations"], profile=INSPECTOR_FIGURE
    )
    return overview, {
        **scenes,
        "materialized_realization_id": job.identity,
        "snapshot_digest": answer["snapshot_digest"],
        "eligible": path["matches"],
        "path": path,
        "rendering": "current",
        "construction_cost": atlas.construction_cost.model_dump(mode="json")
        if atlas.construction_cost
        else None,
    }
