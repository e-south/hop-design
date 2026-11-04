"""Keep requested interfaces separate from achieved cut coordinates and actual route methods."""

from typing import Any

from hop_design.models.construction.complete.clone.geometry import clone_payload_end_offsets
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization


def requested_interface(request: dict[str, Any]) -> dict[str, Any] | None:
    ends = request.get("ends")
    if ends is None:
        return None
    return {
        "requested_distances_bp": {
            side: ends[side]["payload_end_offset_bp"] for side in ("left", "right")
        },
        "requested_ends": {side: ends[side]["cohesive_end_sequence"] for side in ("left", "right")},
    }


def preparation_interface(
    route: MaterializedConstructionRealization, request: dict[str, Any]
) -> dict[str, Any]:
    product = route.final_product
    ends = product.cohesive_ends
    interface = None
    if len(ends) == 2:
        distances = clone_payload_end_offsets(
            ends=(ends[0], ends[1]),
            encoding_start=product.design_projection.source_span.start.offset,
            payload_boundaries=route.design.payload_boundaries,
        )
        interface = {
            **(requested_interface(request) or {}),
            "stage": product.reference.endpoint.value,
            "state_id": route.construction_program.states[-1].state_id,
            "achieved_distances_bp": dict(zip(("left", "right"), distances, strict=True)),
            "coordinate_basis": "recorded_cuts_and_stem_boundaries",
            "ends": [e.model_dump(mode="json") for e in ends],
        }
    names = {e["enzyme_id"]: e["canonical_name"] for e in request["enzyme_catalog"]["enzymes"]}
    used = sorted(
        {
            operation.enzyme_id
            for program in route.construction_program.reaction_programs
            for stage in program.stages
            for operation in stage.operations
        }
    )
    return {
        "interface": interface,
        "methods": [{"enzyme_id": enzyme, "name": names[enzyme]} for enzyme in used],
    }
