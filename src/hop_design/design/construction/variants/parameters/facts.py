"""Read achieved coordinates from admitted authorities; never infer a failed product."""

import json
from typing import Any, cast

from hop_design.models.construction.complete.pcr.authority import AdapterAnnealingAuthority
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.complete.source_preparation.policy import (
    SourceDuplexPreparationPolicy,
    primer_required_length,
)
from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget


def parameter_facts(
    route: MaterializedConstructionRealization, request: dict[str, Any]
) -> dict[str, Any]:
    foldback = route.foldback_authority
    geometry = cast(FoldbackTarget, foldback.local_realization.achieved_geometry)
    hairpin = describe_hairpin(route)
    values: dict[str, Any] = {
        "foldback_arm_bp": geometry.annealing_arm_length_bp,
        "join_offset_nt": geometry.junction_offset_nt,
        "self_paired_arm_bp": geometry.annealing_arm_length_bp - geometry.junction_offset_nt,
        "foldback_strand": geometry.nick_strand.value,
        "foldback_method": foldback.foldback_nick.enzyme_id,
        "noncanonical_pairs": hairpin.noncanonical_open_side_contacts,
    }
    source = route.source_preparation
    policy = SourceDuplexPreparationPolicy.model_validate_json(
        json.dumps(request["materialization"]["source_preparation"])
    )
    for direction, available in (
        ("forward", source.payload_source_span.start.offset),
        (
            "reverse",
            len(source.source_ssdna.sequence_5prime) - source.payload_source_span.end.offset,
        ),
    ):
        values[f"source_{direction}_primer_required_nt"] = primer_required_length(
            getattr(policy, f"{direction}_primer")
        )
        values[f"source_{direction}_primer_available_nt"] = available
    basal = route.basal_authority
    if basal is not None:
        target = cast(BasalTarget, basal.local_realization.achieved_geometry)
        if basal.future_release_action is not None:
            requirement = basal.future_release_action.requirement
            values["basal_release_recognition_material"] = requirement.recognition_material
            values["basal_release_product_end"] = requirement.product_end
        values.update(
            basal_nick_offset_nt=target.nick_offset_nt,
            basal_strand=target.nick_strand.value,
            basal_method=basal.basal_nick.enzyme_id,
            adapter_annealing_min_nt=request["basal"]["geometry"]["minimum_adapter_annealing_nt"],
        )
        for pair in basal.projection.pairing_state.pairs:
            position = pair.position_from_ligation
            values[f"basal_source_base_{position}"] = pair.source_base
            values[f"basal_adapter_base_{position}"] = pair.adapter_base
            values[f"basal_pair_class_{position}"] = pair.pair_class.value
    for transition in route.construction_program.transitions:
        if isinstance(transition.pcr_authority, AdapterAnnealingAuthority):
            values["adapter_annealing_achieved_nt"] = len(transition.pcr_authority.pairings)
    for end in route.final_product.cohesive_ends:
        values[f"{end.product_end}_end_word"] = end.sequence
        values[f"{end.product_end}_end_polarity"] = end.overhang_end.value
    release_ids = {
        operation.enzyme_id
        for program in route.construction_program.reaction_programs
        for stage in program.stages
        for operation in stage.operations
        if operation.role.value == "end_generation"
    }
    if len(release_ids) == 1 and route.final_product.cohesive_ends:
        values["release_method"] = next(iter(release_ids))
    return values
