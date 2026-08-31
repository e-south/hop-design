"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/complete.py

Builds and verifies scientific summaries of whole-route composition.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.design.construction.complete.discovery import VerifiedConstructionSpaceResult
from hop_design.design.construction.complete.replay_admission import (
    has_current_replay_admission,
)
from hop_design.models.construction import RealizationGrouping
from hop_design.models.construction.complete.material.inventory import (
    required_external_materials,
)
from hop_design.models.construction.projections import (
    CompleteConstructionSummaryProjection,
    CompleteConstructionSummaryRow,
)
from hop_design.serialization import canonical_json_bytes


def _admit_source(source: VerifiedConstructionSpaceResult) -> VerifiedConstructionSpaceResult:
    if not isinstance(source, VerifiedConstructionSpaceResult):
        raise TypeError("Complete construction projections require a verified source result.")
    if not has_current_replay_admission(source, source.result):
        raise ValueError(
            "Construction space result disagrees with deterministic composition replay."
        )
    return source


def project_complete_construction_summary(
    source: VerifiedConstructionSpaceResult,
) -> CompleteConstructionSummaryProjection:
    """Project every ordered disposition from a replay-admitted complete result."""
    admitted = _admit_source(source)
    result = admitted.result
    realizations = {item.materialized_realization_id: item for item in result.realizations}
    geometry_keys = {
        member: group.group_key
        for group in result.geometry_groups
        if group.grouping is RealizationGrouping.ACHIEVED_GEOMETRY
        for member in group.realization_ids
    }
    product_keys = {
        member: group.group_key
        for group in result.final_product_groups
        if group.grouping is RealizationGrouping.FINAL_PRODUCT
        for member in group.realization_ids
    }
    rows = []
    for disposition in result.combination_dispositions:
        realization = (
            None
            if disposition.materialized_realization_id is None
            else realizations[disposition.materialized_realization_id]
        )
        rows.append(
            CompleteConstructionSummaryRow(
                ordinal=disposition.ordinal,
                foldback_realization_id=disposition.foldback_realization_id,
                basal_realization_id=disposition.basal_realization_id,
                status=disposition.status,
                rejection_reason=disposition.rejection_reason,
                truncation_reason=disposition.truncation_reason,
                materialized_realization_id=disposition.materialized_realization_id,
                achieved_geometry_group_key=(
                    None
                    if realization is None
                    else geometry_keys[realization.materialized_realization_id]
                ),
                final_product_group_key=(
                    None
                    if realization is None
                    else product_keys[realization.materialized_realization_id]
                ),
                endpoint=(
                    None if realization is None else realization.final_product.reference.endpoint
                ),
                material_ids=(
                    ()
                    if realization is None
                    else tuple(
                        item.material_id for item in required_external_materials(realization)
                    )
                ),
                route_material_dispositions=(
                    () if realization is None else realization.route_material_dispositions
                ),
                source_material_nt=(
                    0
                    if realization is None
                    else len(realization.source_preparation.source_ssdna.sequence_5prime)
                ),
                auxiliary_material_nt=(
                    0
                    if realization is None
                    else sum(
                        len(item.sequence_5prime)
                        for item in required_external_materials(realization)[1:]
                    )
                ),
                endpoint_product_nt=(
                    0
                    if realization is None
                    else sum(len(strand.sequence) for strand in realization.final_product.strands)
                ),
                candidate_enzyme_programs=disposition.candidate_enzyme_programs,
                recognition_placements_attempted=disposition.recognition_placements_attempted,
                constraint_systems_attempted=disposition.constraint_systems_attempted,
            )
        )
    return CompleteConstructionSummaryProjection.create(
        source_result_id=result.result_id,
        problem_id=result.problem_id,
        execution_id=result.execution_id,
        endpoint=result.request.endpoint,
        status=result.status,
        rows=tuple(rows),
        geometry_groups=result.geometry_groups,
        final_product_groups=result.final_product_groups,
        accounting=result.accounting,
        material_accounting=result.material_accounting,
        failure_reasons=result.failure_reasons,
        truncation_reasons=result.truncation_reasons,
        upstream_truncation_reasons=result.upstream_truncation_reasons,
        provenance=result.provenance,
        claim_boundary=result.claim_boundary,
    )


def verify_complete_construction_projection(
    projection: CompleteConstructionSummaryProjection,
    source: VerifiedConstructionSpaceResult,
) -> CompleteConstructionSummaryProjection:
    """Require canonical equality with a projection rebuilt from its verified source."""
    parsed = CompleteConstructionSummaryProjection.model_validate(
        projection.model_dump(mode="python", by_alias=True)
    )
    expected = project_complete_construction_summary(source)
    if canonical_json_bytes(parsed) != canonical_json_bytes(expected):
        raise ValueError(
            "Complete construction projection does not replay its verified source result."
        )
    return parsed


__all__ = [
    "project_complete_construction_summary",
    "verify_complete_construction_projection",
]
