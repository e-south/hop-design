"""Resolve local browsing against complete compatible options, without choosing a set."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.inspection_transition import InspectionTransition
from hop_design.models.construction.variants.atlas import ScaffoldAtlasRequest
from hop_design.models.construction.variants.inspection import (
    MolecularAddress,
    ScaffoldInspectionRequest,
)
from hop_design.models.construction.variants.preview import ScaffoldVariantPreviewRequest
from hop_design.serialization import canonical_json_bytes

from ..packets.publication import SourceBoundConstructionPacket
from ..projections.atlas_comparison import atlas_correspondence, view_states
from ..projections.inspection import inspection_states, resolve_inspection_states
from ..projections.inspection_correspondence import inspection_correspondence
from .atlas import _inspect_atlas
from .inspection import _inspect_variant
from .public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants


@dataclass(frozen=True, init=False, repr=False)
class ScaffoldVariantPreview(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.scaffold-variant-preview-packet/v1"


def preview_scaffold_variant(
    pool: ScaffoldExploration,
    choices: ScaffoldVariantChoices,
    request: str | Path | dict[str, Any],
) -> ScaffoldVariantPreview:
    value = load_source_mapping(request) if isinstance(request, str | Path) else request
    intent = ScaffoldVariantPreviewRequest.model_validate_json(canonical_json_bytes(value))
    summary = json.loads(choices.json_bytes)
    if intent.result_digest != pool.result_digest or intent.query_digest != summary["query_digest"]:
        raise ValueError("Stale preview result or query digest.")
    if query_scaffold_variants(pool, summary["query"]).json_bytes != choices.json_bytes:
        raise ValueError("Choices no longer agree with this admitted exploration.")
    variant = next((v for v in summary["variants"] if v["variant_id"] == intent.variant_id), None)
    if variant is None:
        raise ValueError("Unknown variant in the current neighborhood and stage.")
    labels = [label for label in variant["option_labels"] if label in summary["compatible_options"]]
    if intent.option_label is not None and intent.option_label not in labels:
        raise ValueError("Preview must name a compatible preparation supporting this variant.")
    routes = dict(pool._routes)
    if intent.view_from is not None and intent.view_from.option_label not in routes:
        raise ValueError("Unknown preparation for the preceding molecular view.")
    facts = {o["label"]: o for o in json.loads(pool._options)}
    candidates = [
        {
            **next(p for p in summary["preparations"] if p["label"] == label),
            "neighborhoods": facts[label]["variants"][summary["query"]["stage"]],
            "available_states": [
                {"state_id": s.state_id, "phase": s.phase.value}
                for s in inspection_states(routes[label])
            ],
            "state_ids": [s.state_id for s in view_states(routes[label], intent.state)],
        }
        for label in labels
    ]
    label = intent.option_label or (labels[0] if len(labels) == 1 else None)
    status = "excluded_by_constraints" if not labels else "preparation_choice_required"
    inspection = None
    files: dict[str, bytes] = {}
    focus_status = "not_requested"
    transition = None
    atlas_transitions: tuple[InspectionTransition, ...] = ()
    if label is not None:
        states = view_states(routes[label], intent.state)
        status = "state_unavailable" if not states else "state_ambiguous"
        if len(states) == 1 or intent.state == "all":
            focus, focus_status = _transfer_focus(routes, intent, label)
            if focus is None and intent.focus is not None and intent.focus_mode == "comparison":
                assert intent.focus_option_label is not None
                old = routes[intent.focus_option_label]
                previous = resolve_inspection_states(old, intent.focus.state_id)[0]
                target = (
                    [s for s in states if s.phase == previous.phase]
                    if intent.state == "all"
                    else states
                )
                correspondence = (
                    inspection_correspondence(old, previous, routes[label], target[0])
                    if len(target) == 1
                    else None
                )
                targets = {
                    link.target
                    for link in (correspondence.links if correspondence else ())
                    if link.reference == intent.focus
                }
                if len(targets) == 1:
                    focus = targets.pop()
                    focus_status = "comparison_position"
            if intent.view_from is not None:
                old = routes[intent.view_from.option_label]
                links = atlas_correspondence(
                    old, intent.view_from.state, routes[label], intent.state
                )
                if intent.state == "all" or intent.view_from.state == "all":
                    atlas_transitions = links
                else:
                    transition = links[0]
            inspected = (
                _inspect_atlas(
                    pool,
                    summary,
                    ScaffoldAtlasRequest(
                        result_digest=pool.result_digest,
                        query_digest=intent.query_digest,
                        option_label=label,
                        focus=focus,
                    ),
                    choices,
                )
                if intent.state == "all"
                else _inspect_variant(
                    pool,
                    summary,
                    ScaffoldInspectionRequest(
                        result_digest=pool.result_digest,
                        query_digest=intent.query_digest,
                        option_label=label,
                        state=states[0].state_id,
                        focus=focus,
                    ),
                    choices,
                )
            )
            inspection = json.loads(inspected.json_bytes)
            files["projection.svg"] = inspected.svg_bytes
            files["teaching.svg"] = dict(inspected._files)["teaching.svg"]
            files["overview.svg"] = dict(inspected._files)["overview.svg"]
            files["request.json"] = pool._request
            status = "preview_available"
    result = {
        "schema": "hop.scaffold-variant-preview/v1",
        "request": intent.model_dump(mode="json", by_alias=True),
        "result_digest": pool.result_digest,
        "query_digest": intent.query_digest,
        "status": status,
        "option_label": label,
        "selected_product": None,
        "candidates": candidates,
        "focus_transfer": focus_status,
        "transition": transition.model_dump(mode="json") if transition is not None else None,
        "atlas_transitions": [t.model_dump(mode="json") for t in atlas_transitions],
        "inspection": inspection,
    }
    packet = ScaffoldVariantPreview._create(
        files,
        result,
        "# Supported variant preview\n\n"
        + status.replace("_", " ")
        + ". Preview does not edit permissions, require members or select a preparation.\n",
    )
    object.__setattr__(packet, "_roots", choices._roots)
    return packet


def _transfer_focus(
    routes: dict[str, MaterializedConstructionRealization],
    intent: ScaffoldVariantPreviewRequest,
    label: str,
) -> tuple[MolecularAddress | None, str]:
    if intent.focus is None:
        return None, "not_requested"
    if intent.focus_option_label not in routes:
        raise ValueError("Unknown preparation for the inspected position.")
    old = routes[intent.focus_option_label]
    origin = next(
        (
            b
            for s in inspection_states(old)
            if s.state_id == intent.focus.state_id
            for m in s.molecules
            if m.strand_id == intent.focus.strand_id
            for b in m.lineage
            if b.product_index == intent.focus.index
        ),
        None,
    )
    if origin is None:
        raise ValueError("Unknown molecular address in the originating preparation.")
    if intent.focus_option_label == label:
        return intent.focus, "same_preparation"
    # origin_id is a content-addressed material use, including exact material and role.
    for state in inspection_states(routes[label]):
        matches = [
            (m.strand_id, b.product_index)
            for m in state.molecules
            for b in m.lineage
            if (b.origin_id, b.origin_strand, b.origin_index)
            == (origin.origin_id, origin.origin_strand, origin.origin_index)
        ]
        if len(matches) == 1:
            strand, index = matches[0]
            return MolecularAddress(
                state_id=state.state_id, strand_id=strand, index=index
            ), "shared_material"
    return None, "cleared_no_verified_correspondence"
