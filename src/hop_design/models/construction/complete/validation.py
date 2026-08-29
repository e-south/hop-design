"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/validation.py

Replays derivable whole-route payload, accounting, and material relations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from hop_design.models.construction.accounting import SearchCompletionStatus
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.payload import (
    SourceOrientation,
    validate_linear_source_map,
)
from hop_design.models.sequence import reverse_complement_iupac

from .authority import (
    CompositionDisposition,
    CompositionDispositionStatus,
    CompositionMaterialAccounting,
    ConstructionCompositionProvenance,
)
from .evaluation import CompositionRejectionCode, evaluate_combination
from .request import ConstructionDiscoveryRequest, derived_source_material_id


def validate_payload_source_map(request: ConstructionDiscoveryRequest, realization: Any) -> None:
    """Require mapped material bytes to replay the exact requested payload."""
    validate_linear_source_map(request.payload, realization.payload_source_map)
    source_materials = {item.material_id: item for item in realization.materials}
    payload_parts: list[str] = []
    for segment in sorted(
        realization.payload_source_map.segments,
        key=lambda item: item.payload_span.start.offset,
    ):
        material = source_materials.get(segment.source_material_id)
        if material is None or segment.source_span.end.offset > len(material.sequence_5prime):
            raise ValueError("The payload source map must reference exact route material.")
        sequence = material.sequence_5prime[
            segment.source_span.start.offset : segment.source_span.end.offset
        ]
        payload_parts.append(
            sequence
            if segment.orientation is SourceOrientation.FORWARD
            else reverse_complement_iupac(sequence)
        )
    if "".join(payload_parts) != request.payload.payload.sequence:
        raise ValueError("The payload source map must replay exact requested payload bytes.")


def validate_accepted_realization(
    *,
    request: ConstructionDiscoveryRequest,
    provenance: ConstructionCompositionProvenance,
    disposition: CompositionDisposition,
    realization: Any,
) -> None:
    """Cross-bind one accepted route to its exact request and upstream domains."""
    if realization.design != request.design:
        raise ValueError("Accepted design authority must equal the exact result request.")
    validate_payload_source_map(request, realization)
    source, source_complement, *auxiliaries = realization.materials
    policy = request.materialization
    expected_auxiliaries = tuple(
        item
        for item in (policy.adapter, policy.forward_primer, policy.reverse_primer)
        if item is not None
    )
    if (
        source.sequence_5prime != realization.realization.precursor_sequence
        or source.material_id
        != derived_source_material_id(source.sequence_5prime, complementary=False)
        or source_complement.material_id
        != derived_source_material_id(source_complement.sequence_5prime, complementary=True)
        or source.origin is not policy.source_origin
        or source.five_prime_end is not policy.source_five_prime_end
        or source.three_prime_end is not policy.source_three_prime_end
        or source_complement.origin is not policy.source_complement_origin
        or source_complement.five_prime_end is not policy.source_complement_five_prime_end
        or source_complement.three_prime_end is not policy.source_complement_three_prime_end
        or tuple(auxiliaries) != expected_auxiliaries
    ):
        raise ValueError("Accepted material set must equal the exact result request policy.")
    if (
        realization.foldback_realization_id != disposition.foldback_realization_id
        or realization.basal_realization_id != disposition.basal_realization_id
    ):
        raise ValueError("Accepted local authorities must equal their exact disposition.")
    if realization.foldback_realization_id not in provenance.foldback_realization_ids:
        raise ValueError("Accepted route must bind one verified foldback authority.")
    if realization.basal_realization_id is not None and (
        realization.basal_realization_id not in provenance.basal_realization_ids
    ):
        raise ValueError("Accepted route must bind one verified basal authority.")
    expected_local_ids = (
        *((realization.basal_realization_id,) if realization.basal_realization_id else ()),
        realization.foldback_realization_id,
    )
    if realization.realization.local_realization_ids != expected_local_ids:
        raise ValueError("Complete relation must preserve its exact local authorities.")


def validate_combination_evaluations(
    *,
    request: ConstructionDiscoveryRequest,
    foldback_authority: FoldbackNeighborhoodDiscoveryResult,
    basal_authority: BasalNeighborhoodDiscoveryResult | None,
    dispositions: tuple[CompositionDisposition, ...],
    realizations: tuple[Any, ...],
) -> None:
    """Replay every examined disposition from exact embedded upstream authorities."""
    payload = request.payload.payload.sequence
    foldback_by_id = {
        item.foldback_realization_id: item
        for item in foldback_authority.realizations
        if item.payload_sequence == payload
    }
    basal_by_id = (
        {}
        if basal_authority is None
        else {
            item.basal_realization_id: item
            for item in basal_authority.realizations
            if item.payload_sequence == payload
        }
    )
    evaluated: list[tuple[CompositionDisposition, Any]] = []
    for disposition in dispositions:
        foldback = foldback_by_id[disposition.foldback_realization_id]
        basal = (
            None
            if disposition.basal_realization_id is None
            else basal_by_id[disposition.basal_realization_id]
        )
        evaluation = evaluate_combination(
            request,
            foldback=foldback,
            basal=basal,
            foldback_policy=foldback_authority.neighborhood.request.enzyme_provisioning,
            basal_policy=(
                None
                if basal_authority is None
                else basal_authority.discovery.request.enzyme_provisioning
            ),
        )
        observed_metrics = (
            disposition.candidate_enzyme_programs,
            disposition.recognition_placements_attempted,
            disposition.constraint_systems_attempted,
        )
        expected_metrics = (
            evaluation.candidate_enzyme_programs,
            evaluation.recognition_placements_attempted,
            evaluation.constraint_systems_attempted,
        )
        if observed_metrics != expected_metrics:
            raise ValueError("Disposition metrics must equal exact combination evaluation.")
        evaluated.append((disposition, evaluation))

    basal_count = 1 if basal_authority is None else len(basal_by_id)
    all_examined = len(evaluated) == len(foldback_by_id) * basal_count
    has_intrinsic_failure = any(
        evaluation.rejection_reason is not None for _, evaluation in evaluated
    )
    apply_require_all = (
        request.whole_route_constraints.require_all_combinations_valid
        and all_examined
        and has_intrinsic_failure
        and foldback_authority.neighborhood.status is not SearchCompletionStatus.TRUNCATED
        and (
            basal_authority is None
            or basal_authority.discovery.status is not SearchCompletionStatus.TRUNCATED
        )
    )
    realizations_by_id = {item.materialized_realization_id: item for item in realizations}
    for disposition, evaluation in evaluated:
        expected_reason = evaluation.rejection_reason
        if expected_reason is None and apply_require_all:
            expected_reason = CompositionRejectionCode.ALL_COMBINATIONS_VALID_REQUIRED
        if expected_reason is not None:
            if (
                disposition.status is not CompositionDispositionStatus.REJECTED
                or disposition.rejection_reason is not expected_reason
            ):
                raise ValueError("Disposition reason must equal exact combination evaluation.")
            continue
        if disposition.status is not CompositionDispositionStatus.ACCEPTED:
            raise ValueError("Compatible combination evaluation must be accepted.")
        realization = realizations_by_id.get(disposition.materialized_realization_id)
        if realization is None:
            raise ValueError("Accepted combination evaluation must bind its realization.")
        if (
            tuple(realization.materials[:2]) != (evaluation.source, evaluation.source_complement)
            or realization.construction_program.reaction_programs != (evaluation.reaction_program,)
            or realization.construction_program.stage_assessments != evaluation.stage_assessments
            or realization.final_product.reference.sequence != evaluation.final_sequence
        ):
            raise ValueError("Accepted realization must equal exact combination evaluation.")


def expected_accounting(
    *,
    provenance: ConstructionCompositionProvenance,
    dispositions: tuple[CompositionDisposition, ...],
    geometry_group_count: int,
    final_product_group_count: int,
) -> dict[str, int]:
    """Derive every canonical composition count from exact dispositions."""
    examined = len(dispositions)
    rejected = sum(item.status is CompositionDispositionStatus.REJECTED for item in dispositions)
    accepted = sum(item.status is CompositionDispositionStatus.ACCEPTED for item in dispositions)
    return {
        "foldback_local_realizations": len(provenance.foldback_realization_ids),
        "basal_local_realizations": len(provenance.basal_realization_ids),
        "nominal_combinations": len(provenance.foldback_realization_ids)
        * (len(provenance.basal_realization_ids) or 1),
        "pruned_before_execution": 0,
        "executed_combinations": examined,
        "examined_combinations": examined,
        "rejected_after_execution": rejected,
        "rejected_combinations": rejected,
        "valid_realizations": accepted,
        "candidate_enzyme_programs": sum(item.candidate_enzyme_programs for item in dispositions),
        "recognition_placements_attempted": sum(
            item.recognition_placements_attempted for item in dispositions
        ),
        "constraint_systems_attempted": sum(
            item.constraint_systems_attempted for item in dispositions
        ),
        "distinct_geometry_groups": geometry_group_count,
        "distinct_final_products": final_product_group_count,
    }


def expected_material_accounting(realizations: tuple[Any, ...]) -> CompositionMaterialAccounting:
    """Derive material totals from exact accepted route materials and products."""
    return CompositionMaterialAccounting(
        source_material_nt=sum(
            len(item.sequence_5prime)
            for realization in realizations
            for item in realization.materials[:2]
        ),
        auxiliary_material_nt=sum(
            len(item.sequence_5prime)
            for realization in realizations
            for item in realization.materials[2:]
        ),
        endpoint_product_nt=sum(
            len(item.final_product.reference.sequence) for item in realizations
        ),
    )


__all__ = [
    "expected_accounting",
    "expected_material_accounting",
    "validate_accepted_realization",
    "validate_combination_evaluations",
    "validate_payload_source_map",
]
