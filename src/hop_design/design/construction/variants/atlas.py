"""Public, source-bound atlas over one compatible complete preparation."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.molecular.atlas import render_molecular_atlas
from hop_design.export.construction.molecular.teaching import render_parameter_teaching
from hop_design.models.construction.variants.atlas import ScaffoldAtlasRequest
from hop_design.serialization import canonical_json_bytes

from ..packets.atlas import MolecularAtlasPacket
from ..packets.inspection import MolecularInspectionPacket
from ..projections.atlas import project_molecular_atlas
from .atlas_comparison import compare_atlas
from .envelope import atlas_envelope
from .public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants
from .teaching import teaching_view


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldAtlas(MolecularAtlasPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-atlas-packet/v1"


def inspect_scaffold_atlas(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    request: str | Path | dict[str, Any],
) -> ScaffoldAtlas:
    """Inspect the complete preparation, including route and teaching artwork."""
    packet = _inspect_scaffold_atlas(pool, choices, request, draw_route=True)
    assert isinstance(packet, ScaffoldAtlas)
    return packet


def _inspect_scaffold_atlas(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    request: str | Path | dict[str, Any],
    *,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    value = load_source_mapping(request) if isinstance(request, str | Path) else request
    intent = ScaffoldAtlasRequest.model_validate_json(canonical_json_bytes(value))
    summary = json.loads(choices.json_bytes)
    if intent.result_digest != pool.result_digest or intent.query_digest != summary["query_digest"]:
        raise ValueError("Stale atlas result or query digest.")
    if query_scaffold_variants(pool, summary["query"]).json_bytes != choices.json_bytes:
        raise ValueError("Choices no longer agree with this admitted exploration.")
    if intent.option_label not in summary["compatible_options"]:
        raise ValueError("Atlas must name a compatible complete preparation.")
    return _inspect_atlas(pool, summary, intent, choices, draw_route=draw_route)


def _inspect_atlas(
    pool: ScaffoldExploration,
    summary: dict[str, Any],
    intent: ScaffoldAtlasRequest,
    choices: ScaffoldVariantChoices,
    *,
    draw_route: bool = True,
) -> MolecularAtlasPacket:
    route = dict(pool._routes)[intent.option_label]
    names = {m["enzyme_id"]: m["name"] for p in summary["preparations"] for m in p["methods"]}
    atlas = project_molecular_atlas(route, intent.focus, enzyme_names=names)
    comparison = compare_atlas(pool, summary, intent.option_label)
    envelope = atlas_envelope(pool, summary, route)
    teaching, locations = teaching_view(pool, summary, intent.option_label, route, atlas, envelope)
    result = {
        "schema": "hop.scaffold-atlas/v1",
        "request": intent.model_dump(mode="json", by_alias=True),
        "result_digest": pool.result_digest,
        "query_digest": intent.query_digest,
        "option_label": intent.option_label,
        "selected_product": None,
        "reference": summary["query"]["reference"],
        "atlas": atlas.model_dump(mode="json"),
        "parameter_locations": locations,
        "envelope": envelope,
        "teaching": teaching,
        "comparison": comparison.model_dump(mode="json") if comparison else None,
    }
    packet_type = ScaffoldAtlas if draw_route else MolecularInspectionPacket
    packet = packet_type._create(
        {
            **(
                {
                    "projection.svg": render_molecular_atlas(
                        atlas, comparison=comparison, parameter_locations=locations
                    ),
                    "teaching.svg": render_parameter_teaching(
                        teaching, atlas, locations, comparison=comparison
                    ),
                }
                if draw_route
                else {}
            ),
            "request.json": pool._request,
        },
        result,
        "# Complete molecular atlas\n\nAll recorded states of one preparation. "
        "Pairing is recorded architecture, not a conformation prediction. "
        "Primer inputs denote recorded bindings, not additional annealed states. "
        "Inspection preserves the active query and does not select a preparation.\n",
    )
    object.__setattr__(packet, "_roots", choices._roots)
    return packet
