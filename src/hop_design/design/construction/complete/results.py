"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/results.py

Builds authoritative complete-construction results and reversible groupings.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter, defaultdict
from importlib.metadata import version

from hop_design.models.construction import (
    DigitalDesignStatus,
    FailureReasonCount,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    ProjectionInventoryItem,
    ProjectionInventoryStatus,
    RealizationGroup,
    RealizationGrouping,
    SearchCompletionStatus,
)
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.complete import (
    CompositionAccounting,
    CompositionDisposition,
    CompositionDispositionStatus,
    CompositionMaterialAccounting,
    ConstructionCompositionExecution,
    ConstructionCompositionProvenance,
    ConstructionDiscoveryRequest,
    ConstructionSpaceResult,
    MaterializedConstructionRealization,
)
from hop_design.models.construction.complete.evaluation import CompositionRejectionCode
from hop_design.models.construction.complete.material.inventory import (
    required_external_materials,
)
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.payload import _content_id
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult


def _groups(
    realizations: tuple[MaterializedConstructionRealization, ...],
    *,
    grouping: RealizationGrouping,
) -> tuple[RealizationGroup, ...]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for realization in realizations:
        key = (
            _content_id("geometry", 1, realization.geometry_ids)
            if grouping is RealizationGrouping.ACHIEVED_GEOMETRY
            else realization.final_product.reference.final_product_id
        )
        grouped[key].append(realization.materialized_realization_id)
    return tuple(
        RealizationGroup(
            grouping=grouping,
            group_key=key,
            realization_ids=tuple(ids),
            multiplicity=len(ids),
        )
        for key, ids in sorted(grouped.items())
    )


def _material_accounting(
    realizations: tuple[MaterializedConstructionRealization, ...],
) -> CompositionMaterialAccounting:
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


def composition_status(
    *,
    realizations: tuple[MaterializedConstructionRealization, ...],
    truncation: str | None,
    endpoint_truncation_reasons: tuple[str, ...],
    upstream_truncation_reasons: tuple[str, ...],
) -> SearchCompletionStatus:
    """Classify whole-route coverage without treating no result as truncation."""
    if truncation or endpoint_truncation_reasons or upstream_truncation_reasons:
        return SearchCompletionStatus.TRUNCATED
    if realizations:
        return SearchCompletionStatus.COMPLETE
    return SearchCompletionStatus.INFEASIBLE


def reject_accepted_dispositions(
    dispositions: list[CompositionDisposition],
    *,
    rejection_code: CompositionRejectionCode,
) -> list[CompositionDisposition]:
    """Reclassify accepted combinations while preserving every attempted route."""
    return [
        CompositionDisposition(
            ordinal=item.ordinal,
            source_context_sequence=item.source_context_sequence,
            foldback_realization_id=item.foldback_realization_id,
            basal_realization_id=item.basal_realization_id,
            status=CompositionDispositionStatus.REJECTED,
            rejection_reason=(
                rejection_code
                if item.status is CompositionDispositionStatus.ACCEPTED
                else item.rejection_reason
            ),
            candidate_enzyme_programs=item.candidate_enzyme_programs,
            recognition_placements_attempted=item.recognition_placements_attempted,
            constraint_systems_attempted=item.constraint_systems_attempted,
        )
        for item in dispositions
    ]


def build_result(
    *,
    request: ConstructionDiscoveryRequest,
    status: SearchCompletionStatus,
    realizations: tuple[MaterializedConstructionRealization, ...],
    failures: Counter[str],
    truncation: str | None,
    endpoint_truncation_reasons: tuple[str, ...],
    upstream_truncation_reasons: tuple[str, ...],
    foldback_count: int,
    basal_count: int,
    nominal: int,
    examined: int,
    foldback_authority: FoldbackNeighborhoodDiscoveryResult,
    basal_authority: BasalNeighborhoodDiscoveryResult | None,
    source_partition_authority: SourcePartitionDiscoveryResult | None,
    source_partition_rejection_candidates: tuple[MaterializedConstructionRealization, ...],
    design_bundle_id: str,
    dispositions: tuple[CompositionDisposition, ...],
) -> ConstructionSpaceResult:
    """Build one sealed result from exact composition outcomes."""
    geometry_groups = _groups(realizations, grouping=RealizationGrouping.ACHIEVED_GEOMETRY)
    product_groups = _groups(realizations, grouping=RealizationGrouping.FINAL_PRODUCT)
    problem = request.problem_id
    hop_version = version("hop-design")
    execution = ConstructionCompositionExecution(
        problem_id=problem,
        hop_version=hop_version,
        enumeration=request.enumeration,
    )
    foldback_realization_ids = (
        (request.selected_foldback_realization_id,)
        if request.selected_foldback_realization_id is not None
        else tuple(
            item.foldback_realization_id
            for item in foldback_authority.realizations
            if item.payload_sequence == request.payload.payload.sequence
        )
    )
    basal_realization_ids = (
        (request.selected_basal_realization_id,)
        if request.selected_basal_realization_id is not None
        else ()
        if basal_authority is None
        else tuple(
            item.basal_realization_id
            for item in basal_authority.realizations
            if item.payload_sequence == request.payload.payload.sequence
        )
    )
    return ConstructionSpaceResult.create(
        problem_id=problem,
        execution_id=execution.execution_id,
        execution=execution,
        status=status,
        request=request,
        foldback_authority=foldback_authority,
        basal_authority=basal_authority,
        source_partition_authority=source_partition_authority,
        source_partition_rejection_candidates=source_partition_rejection_candidates,
        realizations=realizations,
        geometry_groups=geometry_groups,
        final_product_groups=product_groups,
        accounting=CompositionAccounting(
            foldback_local_realizations=foldback_count,
            basal_local_realizations=basal_count,
            nominal_combinations=nominal,
            pruned_before_execution=0,
            executed_combinations=examined,
            examined_combinations=examined,
            rejected_after_execution=sum(
                item.status is CompositionDispositionStatus.REJECTED for item in dispositions
            ),
            rejected_combinations=sum(
                item.status is CompositionDispositionStatus.REJECTED for item in dispositions
            ),
            truncated_combinations=sum(
                item.status is CompositionDispositionStatus.TRUNCATED for item in dispositions
            ),
            valid_realizations=len(realizations),
            candidate_enzyme_programs=sum(item.candidate_enzyme_programs for item in dispositions),
            recognition_placements_attempted=sum(
                item.recognition_placements_attempted for item in dispositions
            ),
            constraint_systems_attempted=sum(
                item.constraint_systems_attempted for item in dispositions
            ),
            distinct_geometry_groups=len(geometry_groups),
            distinct_final_products=len(product_groups),
        ),
        failure_reasons=tuple(
            FailureReasonCount(code=code, count=count) for code, count in sorted(failures.items())
        ),
        truncation_reasons=(
            *((truncation,) if truncation else ()),
            *endpoint_truncation_reasons,
        ),
        upstream_truncation_reasons=upstream_truncation_reasons,
        provenance=ConstructionCompositionProvenance(
            hop_version=hop_version,
            foldback_result_id=foldback_authority.result_id,
            basal_result_id=(None if basal_authority is None else basal_authority.result_id),
            source_partition_result_id=request.source_partition_result_id,
            source_partition_realization_id=(request.selected_source_partition_realization_id),
            design_bundle_id=design_bundle_id,
            foldback_realization_ids=foldback_realization_ids,
            basal_realization_ids=basal_realization_ids,
        ),
        projection_inventory=(
            ProjectionInventoryItem(
                projection_schema="hop.complete-construction-summary/v3",
                renderer_version="complete-construction-projections/3",
                status=ProjectionInventoryStatus.NOT_GENERATED,
            ),
        ),
        material_accounting=_material_accounting(realizations),
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=(
                MethodResolutionStatus.RESOLVED
                if status is SearchCompletionStatus.COMPLETE
                else MethodResolutionStatus.NOT_RESOLVED
            ),
        ),
        combination_dispositions=dispositions,
    )


__all__ = ["build_result", "composition_status", "reject_accepted_dispositions"]
