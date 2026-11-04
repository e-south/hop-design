"""Inspect a recorded state while preserving the active conditional choice receipt."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.construction.molecular.inspection import (
    render_molecular_inspection,
)
from hop_design.export.construction.molecular.teaching import render_parameter_teaching
from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
from hop_design.models.construction.variants.inspection import ScaffoldInspectionRequest
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..packets.publication import SourceBoundConstructionPacket
from ..projections.atlas import project_molecular_atlas
from ..projections.inspection import project_molecular_inspection
from .envelope import atlas_envelope
from .projection import _variant_projection
from .public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants
from .teaching import teaching_view


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldInspection(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-inspection-packet/v1"

    @property
    def svg_bytes(self) -> bytes:
        return dict(self._files)["projection.svg"]


def inspect_scaffold_variant(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    request: str | Path | dict[str, Any],
) -> ScaffoldInspection:
    value = load_source_mapping(request) if isinstance(request, str | Path) else request
    intent = ScaffoldInspectionRequest.model_validate_json(canonical_json_bytes(value))
    summary = json.loads(choices.json_bytes)
    if intent.result_digest != pool.result_digest or intent.query_digest != summary["query_digest"]:
        raise ValueError("Stale inspection result or query digest.")
    if query_scaffold_variants(pool, summary["query"]).json_bytes != choices.json_bytes:
        raise ValueError("Choices no longer agree with this admitted exploration.")
    if intent.option_label not in summary["compatible_options"]:
        raise ValueError("Inspection must name a compatible complete preparation.")
    return _inspect_variant(pool, summary, intent, choices)


def _inspect_variant(
    pool: ScaffoldExploration,
    summary: dict[str, Any],
    intent: ScaffoldInspectionRequest,
    choices: ScaffoldVariantChoices,
) -> ScaffoldInspection:
    """Internal continuation after choice equality and compatible membership are verified."""
    route = dict(pool._routes)[intent.option_label]
    names = {m["enzyme_id"]: m["name"] for p in summary["preparations"] for m in p["methods"]}
    molecular = project_molecular_inspection(route, intent.state, intent.focus, enzyme_names=names)
    envelope = atlas_envelope(pool, summary, route)
    atlas = project_molecular_atlas(route, enzyme_names=names)
    teaching, locations = teaching_view(
        pool,
        summary,
        intent.option_label,
        route,
        atlas,
        envelope,
    )
    role = next(
        s.roles for s in molecular.available_states if s.state_id == molecular.state.state_id
    )
    view_stage = "hairpin" if "hairpin" in role else "endpoint" if "endpoint" in role else None
    if view_stage is not None:
        view, comparison, _ = _variant_projection(
            pool, summary, option_label=intent.option_label, display_stage=view_stage
        )
        svg = render_molecular_inspection(
            molecular,
            comparison=comparison,
            comparison_stage=view_stage,
            parameter_locations=locations,
        )
    else:
        view = {
            "result_digest": pool.result_digest,
            "query_digest": intent.query_digest,
            "option_label": intent.option_label,
            "reference": summary["query"]["reference"],
            "selected_product": None,
        }
        svg = render_molecular_inspection(molecular, parameter_locations=locations)
    inspected = {
        **view,
        "schema": "hop.scaffold-inspection/v1",
        "inspection": intent.model_dump(mode="json", by_alias=True),
        "inspection_digest": sha256_digest(canonical_json_bytes(intent)),
        "molecular_state": molecular.model_dump(mode="json"),
        "envelope": envelope,
        "teaching": teaching,
        "parameter_locations": locations,
    }
    packet = ScaffoldInspection._create(
        {
            "projection.svg": svg,
            "request.json": pool._request,
            "teaching.svg": render_parameter_teaching(teaching, atlas, locations),
            "overview.svg": render_teaching_overview(
                {
                    "atlas": atlas.model_dump(mode="json"),
                    "teaching": teaching,
                    "parameter_locations": locations,
                }
            ),
        },
        inspected,
        "# Preparation inspection\n\nViewing a state does not change the active query "
        "or select a preparation. Recorded pairing is not a conformation prediction.\n",
    )
    object.__setattr__(packet, "_roots", choices._roots)
    return packet
