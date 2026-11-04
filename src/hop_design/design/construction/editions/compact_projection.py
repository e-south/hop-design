"""Project an inspected captured authority through the shared molecular renderer."""

import json
from typing import TYPE_CHECKING, Any

from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.teaching import render_parameter_teaching
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.editions.manifest import EditionSelection
from hop_design.models.construction.projections.atlas import MolecularAtlas, MolecularScenes
from hop_design.serialization import canonical_json_bytes

from ..intents.base import Source
from ..packets.atlas import MolecularAtlasPacket
from ..packets.inspection import MolecularInspectionPacket
from ..projections.atlas import project_molecular_atlas, project_teaching_scenes
from ..projections.atlas_comparison import compare_route_atlases
from ..projections.parameter_locations import parameter_locations
from ..projections.parameter_teaching import parameter_teaching, survey_teaching_axes
from .authority import admitted_route
from .comparison import captured_route, comparison_provenance

if TYPE_CHECKING:
    from .reader import AtlasEdition


def compact_molecule(
    edition: "AtlasEdition", identity: str, answer: dict[str, Any]
) -> dict[str, Any]:
    """Serialize a projected authority for packet and captured-scene consumers."""
    atlas, summary = compact_molecular_projection(edition, identity, answer)
    return {**summary, "atlas": atlas.model_dump(mode="json")}


def compact_molecular_projection(
    edition: "AtlasEdition", identity: str, answer: dict[str, Any]
) -> tuple[MolecularAtlas, dict[str, Any]]:
    """Project one authority using the inspector's already-admitted query context.

    This private path creates no selection. An excluded preparation can still be
    inspected; its eligibility remains in the query row. Authority bytes and the
    molecular descriptor are checked on every projection, independently of that row.
    """
    return _project_molecule(edition, admitted_route(edition, identity), answer)


def _project_molecule(
    edition: "AtlasEdition", route: MaterializedConstructionRealization, answer: dict[str, Any]
) -> tuple[MolecularAtlas, dict[str, Any]]:
    """Compose facts from a route admitted in this invocation, never a persistent cache."""
    path, names = _projection_context(edition, route.materialized_realization_id, answer)
    atlas = project_molecular_atlas(route, enzyme_names=names)
    return atlas, _teaching_summary(
        route, answer, atlas, path, producer=edition.producer, edition_digest=edition.digest
    )


def compact_teaching_projection(
    edition: "AtlasEdition", identity: str, answer: dict[str, Any]
) -> tuple[MolecularScenes, dict[str, Any]]:
    """Project only the exact frames used to teach this preparation's features."""
    route = admitted_route(edition, identity)
    path, names = _projection_context(edition, identity, answer)
    return teaching_projection(
        route, answer, path, names, producer=edition.producer, edition_digest=edition.digest
    )


def teaching_projection(
    route: MaterializedConstructionRealization,
    answer: dict[str, Any],
    path: dict[str, Any],
    names: dict[str, str],
    *,
    producer: dict[str, str],
    edition_digest: str,
) -> tuple[MolecularScenes, dict[str, Any]]:
    """Shared pure projection after route, descriptor and context admission."""
    scenes = project_teaching_scenes(route, enzyme_names=names)
    return scenes, _teaching_summary(
        route, answer, scenes, path, producer=producer, edition_digest=edition_digest
    )


def _projection_context(
    edition: "AtlasEdition", identity: str, answer: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    if answer["snapshot_digest"] != edition._store.manifest.snapshot_digest:
        raise ValueError("Preview context disagrees with the edition snapshot.")
    path = next((p for p in answer["paths"] if p["materialized_realization_id"] == identity), None)
    if path is None:
        raise ValueError("Preview context lacks the recorded preparation.")
    names = {
        node["value"]: node["label"]
        for axis in answer["axes"]
        if axis["key"].endswith("method")
        for node in axis["nodes"]
    }
    return path, names


def _teaching_summary(
    route: MaterializedConstructionRealization,
    answer: dict[str, Any],
    atlas: MolecularScenes,
    path: dict[str, Any],
    *,
    producer: dict[str, str],
    edition_digest: str,
) -> dict[str, Any]:
    locations = parameter_locations(route, atlas, path["values"])
    teaching = parameter_teaching(
        route,
        atlas,
        locations,
        path["values"],
        survey_teaching_axes(answer["axes"]),
        {**answer.get("context", {}), "coverage": answer.get("coverage", {})},
    )
    return {
        "schema": "hop.compact-edition-atlas/v1",
        "validation": "captured_authority_integrity; not_new_molecular_replay",
        "producer": producer,
        "edition_digest": edition_digest,
        "projection": path,
        "comparison": None,
        "parameter_locations": locations,
        "teaching": teaching,
    }


def compact_atlas(
    edition: "AtlasEdition",
    selected: EditionSelection,
    *,
    reference_selection: Source | None = None,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    from .reader import CapturedAtlas

    identity = selected.materialized_realization_id
    route = admitted_route(edition, identity)
    atlas, summary = _project_molecule(edition, route, edition._inspection_choices(identity))
    summary["atlas"] = atlas.model_dump(mode="json")
    summary["selection"] = edition.select(identity)
    comparison = None
    if reference_selection is not None:
        # Comparison previously reopened the serialized packet before drawing.
        # Retain its deterministic metadata order without drawing that packet twice.
        summary = json.loads(canonical_json_bytes(summary))
        reference = edition._selected(reference_selection)
        old = captured_route(edition, reference.materialized_realization_id)
        comparison = compare_route_atlases(
            old, route, reference=old.materialized_realization_id, option=identity
        )
        summary.update(
            comparison=comparison.model_dump(mode="json"),
            selection=selected.model_dump(mode="json", by_alias=True),
            reference_selection=reference.model_dump(mode="json", by_alias=True),
            **comparison_provenance(edition, redraw=True),
        )
    files = {}
    if draw_route:
        files = {
            "projection.svg": render_molecular_atlas(
                atlas, comparison=comparison, parameter_locations=summary["parameter_locations"]
            ),
            "teaching.svg": render_parameter_teaching(
                summary["teaching"], atlas, summary["parameter_locations"], comparison=comparison
            ),
        }
    packet_type = CapturedAtlas if draw_route else MolecularInspectionPacket
    packet = packet_type._create(
        files,
        summary,
        "# Captured preparation\n\nExact captured molecular authority, drawn on demand. "
        "The original producer and current renderer remain separately identified. "
        "Opening this edition does not rerun discovery or molecular verification.\n",
    )
    object.__setattr__(packet, "_roots", (edition._store.root,))
    return packet
