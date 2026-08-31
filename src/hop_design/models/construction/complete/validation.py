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
from hop_design.models.construction.payload import ConstructionEndpoint

from .authority import (
    CompositionDisposition,
    CompositionDispositionStatus,
    CompositionMaterialAccounting,
    ConstructionCompositionProvenance,
)
from .evaluation import CompositionRejectionCode, evaluate_combination
from .material.inventory import required_external_materials
from .payload_validation import validate_payload_source_map
from .request import ConstructionDiscoveryRequest
from .state import ConstructionStatePhase


def validate_endpoint_evidence(
    request: ConstructionDiscoveryRequest,
    realization: Any,
) -> None:
    """Require final topology and terminal phase to match the requested endpoint."""
    if realization.final_product.reference.endpoint is not request.endpoint:
        raise ValueError("Final product endpoint must match the exact request.")
    topology = realization.final_product.reference.topology
    terminal_phase = realization.construction_program.states[-1].phase
    if request.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN and (
        topology != "single_stranded_hairpin"
        or terminal_phase is not ConstructionStatePhase.LIGATED_PRODUCT
    ):
        raise ValueError("Direct final product topology and terminal phase must match.")
    if request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and (
        topology != "linear_duplex"
        or terminal_phase is not ConstructionStatePhase.HAIRPIN_PCR_DUPLEX
    ):
        raise ValueError("PCR final product topology and terminal phase must match.")
    if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX and (
        topology != "linear_duplex"
        or terminal_phase is not ConstructionStatePhase.CLONE_READY_DUPLEX
        or tuple(end.product_end for end in realization.final_product.cohesive_ends)
        != ("left", "right")
    ):
        raise ValueError("Clone-ready topology, terminal phase, and cohesive ends must match.")


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
        for item in (
            policy.adapter,
            (
                None
                if policy.hairpin_pcr_forward_primer is None
                else policy.hairpin_pcr_forward_primer.oligo
            ),
            (
                None
                if policy.hairpin_pcr_reverse_primer is None
                else policy.hairpin_pcr_reverse_primer.oligo
            ),
        )
        if item is not None
    )
    if (
        source.sequence_5prime != realization.realization.precursor_sequence
        or tuple(
            binding.material
            for binding in realization.source_preparation.produced_material_bindings
        )
        != (source, source_complement)
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

    basal_count = 1 if request.selects_local_pair or basal_authority is None else len(basal_by_id)
    foldback_count = 1 if request.selects_local_pair else len(foldback_by_id)
    all_examined = len(evaluated) == foldback_count * basal_count
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
        if evaluation.truncation_reason is not None:
            if (
                disposition.status is not CompositionDispositionStatus.TRUNCATED
                or disposition.truncation_reason != evaluation.truncation_reason
            ):
                raise ValueError("Disposition truncation must equal exact combination evaluation.")
            continue
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
        expected_programs = (
            (evaluation.reaction_program, evaluation.end_generation_program)
            if evaluation.end_generation_program is not None
            else (evaluation.reaction_program,)
        )
        expected_assessments = (
            *evaluation.stage_assessments,
            *evaluation.end_generation_stage_assessments,
        )
        if request.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
            endpoint_matches = (
                realization.final_product.encoding_projection.sequence == evaluation.final_sequence
                and realization.final_product.encoding_projection.source_span
                == evaluation.design_parent_span
            )
        elif request.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            endpoint_matches = (
                realization.final_product.reference.sequence == evaluation.final_sequence
                and realization.final_product.encoding_projection.source_span
                == evaluation.design_parent_span
            )
        else:
            endpoint_matches = (
                realization.final_product.reference.sequence == evaluation.final_sequence
            )
        if (
            realization.source_preparation != evaluation.source_preparation
            or tuple(realization.materials[:2]) != (evaluation.source, evaluation.source_complement)
            or realization.construction_program.reaction_programs != expected_programs
            or realization.construction_program.stage_assessments != expected_assessments
            or not endpoint_matches
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
    truncated = sum(item.status is CompositionDispositionStatus.TRUNCATED for item in dispositions)
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
        "truncated_combinations": truncated,
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
            len(realization.source_preparation.source_ssdna.sequence_5prime)
            for realization in realizations
        ),
        auxiliary_material_nt=sum(
            len(item.sequence_5prime)
            for realization in realizations
            for item in required_external_materials(realization)[1:]
        ),
        endpoint_product_nt=sum(
            sum(len(strand.sequence) for strand in item.final_product.strands)
            for item in realizations
        ),
    )


__all__ = [
    "expected_accounting",
    "expected_material_accounting",
    "validate_accepted_realization",
    "validate_combination_evaluations",
    "validate_endpoint_evidence",
    "validate_payload_source_map",
]
