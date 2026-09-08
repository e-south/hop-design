"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/result_contract/replay.py

Replays complete-construction accounting and combination dispositions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

from hop_design.models.construction.accounting import SearchCompletionStatus
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult

from ..authority import (
    CompositionDisposition,
    CompositionDispositionStatus,
    CompositionMaterialAccounting,
    ConstructionCompositionProvenance,
)
from ..composition_domain import source_context_count
from ..evaluation import CompositionRejectionCode, evaluate_combination
from ..evaluation.result import SOURCE_PARTITION_REJECTION_CODES
from ..material.inventory import required_external_materials
from ..request import ConstructionDiscoveryRequest
from .materialized import validate_materialized_evaluation


def validate_combination_evaluations(
    *,
    request: ConstructionDiscoveryRequest,
    foldback_authority: FoldbackNeighborhoodDiscoveryResult,
    basal_authority: BasalNeighborhoodDiscoveryResult | None,
    dispositions: tuple[CompositionDisposition, ...],
    realizations: tuple[Any, ...],
    source_partition_rejection_candidates: tuple[Any, ...] = (),
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
            source_context_sequence=disposition.source_context_sequence,
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

    basal_count = (
        1 if request.selects_local_realizations or basal_authority is None else len(basal_by_id)
    )
    foldback_count = 1 if request.selects_local_realizations else len(foldback_by_id)
    all_examined = len(evaluated) == (
        foldback_count
        * basal_count
        * source_context_count(request.materialization.source_preparation.source_ssdna)
    )
    has_intrinsic_failure = any(
        evaluation.rejection_reason is not None
        or disposition.rejection_reason in SOURCE_PARTITION_REJECTION_CODES
        for disposition, evaluation in evaluated
    )
    apply_require_all = (
        request.whole_route_constraints.require_all_combinations_valid
        and all_examined
        and has_intrinsic_failure
        and foldback_authority.neighborhood.disposition.completion
        is not SearchCompletionStatus.TRUNCATED
        and (
            basal_authority is None
            or basal_authority.discovery.disposition.completion
            is not SearchCompletionStatus.TRUNCATED
        )
    )
    realizations_by_id = {item.materialized_realization_id: item for item in realizations}
    partition_candidates_by_ordinal = {
        disposition.ordinal: item
        for disposition, item in zip(
            (
                item
                for item in dispositions
                if item.rejection_reason in SOURCE_PARTITION_REJECTION_CODES
            ),
            source_partition_rejection_candidates,
            strict=True,
        )
    }
    for disposition, evaluation in evaluated:
        expected_reason = evaluation.rejection_reason
        if evaluation.truncation_reason is not None:
            if (
                disposition.status is not CompositionDispositionStatus.TRUNCATED
                or disposition.truncation_reason != evaluation.truncation_reason
            ):
                raise ValueError("Disposition truncation must equal exact combination evaluation.")
            continue
        if (
            expected_reason is None
            and disposition.rejection_reason in SOURCE_PARTITION_REJECTION_CODES
        ):
            if not request.selects_source_partition:
                raise ValueError(
                    "Source-partition rejection requires an explicitly selected authority."
                )
            if disposition.status is not CompositionDispositionStatus.REJECTED:
                raise ValueError("Source-partition incompatibility must reject the combination.")
            candidate = partition_candidates_by_ordinal.get(disposition.ordinal)
            if candidate is None:
                raise ValueError(
                    "Source-partition rejection must retain its materialized candidate."
                )
            validate_materialized_evaluation(
                request=request,
                realization=candidate,
                evaluation=evaluation,
            )
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
        validate_materialized_evaluation(
            request=request,
            realization=realization,
            evaluation=evaluation,
        )


def expected_accounting(
    *,
    request: ConstructionDiscoveryRequest,
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
        * (len(provenance.basal_realization_ids) or 1)
        * source_context_count(request.materialization.source_preparation.source_ssdna),
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


def composition_truncation_reason(
    *, examined: int, nominal: int, execution: Any, valid: int
) -> str | None:
    """Identify the exact composition bound responsible for a partial prefix."""
    if examined == nominal:
        return None
    if examined > nominal:
        raise ValueError("Examined composition prefix cannot exceed the nominal product.")
    if examined == execution.enumeration.max_combinations:
        return "max_combinations"
    if valid == execution.enumeration.max_realizations:
        return "max_realizations"
    raise ValueError(
        "A partial composition prefix must identify the exact execution bound that fired."
    )


__all__ = [
    "composition_truncation_reason",
    "expected_accounting",
    "expected_material_accounting",
    "validate_combination_evaluations",
]
