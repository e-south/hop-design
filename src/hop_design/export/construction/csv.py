"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/csv.py

Serializes typed construction projections as deterministic tidy CSV relations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json

from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalMinimumOverheadMatrixProjection,
    CompleteConstructionSummaryProjection,
    ConstructionNavigationProjection,
    FoldbackFeasibilityProjection,
    LocalScientificProjection,
    RetainedOverheadFrontierProjection,
    SourcePartitionCertificateProjection,
    TabularConstructionProjection,
)

from .navigation_csv import render_navigation_projection_csv
from .source_partition_csv import render_source_partition_projection_csv


def render_projection_csv(projection: TabularConstructionProjection) -> bytes:
    """Render one projection with repeated context and lossless exact membership."""
    buffer = io.StringIO(newline="")
    if isinstance(projection, ConstructionNavigationProjection):
        return render_navigation_projection_csv(projection)
    if isinstance(projection, SourcePartitionCertificateProjection):
        return render_source_partition_projection_csv(projection)
    if isinstance(projection, CompleteConstructionSummaryProjection):
        _write_complete(buffer, projection)
    elif isinstance(projection, FoldbackFeasibilityProjection):
        _write_foldback(buffer, projection)
    elif isinstance(projection, BasalFeasibilityProjection):
        _write_basal(buffer, projection)
    elif isinstance(projection, BasalMinimumOverheadMatrixProjection):
        _write_basal_matrix(buffer, projection)
    elif isinstance(projection, RetainedOverheadFrontierProjection):
        _write_retained_overhead(buffer, projection)
    else:  # pragma: no cover - strict union protects public callers
        raise TypeError(f"Unsupported scientific projection: {type(projection).__name__}")
    return buffer.getvalue().encode("utf-8")


def _write_complete(
    buffer: io.StringIO,
    projection: CompleteConstructionSummaryProjection,
) -> None:
    fields = (
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "hop_version",
        "route_implementation_version",
        "problem_id",
        "execution_id",
        "endpoint",
        "status",
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "ordinal",
        "foldback_realization_id",
        "basal_realization_id",
        "disposition",
        "rejection_reason",
        "truncation_reason",
        "materialized_realization_id",
        "achieved_geometry_group_key",
        "final_product_group_key",
        "material_ids",
        "route_material_dispositions_json",
        "source_material_nt",
        "auxiliary_material_nt",
        "endpoint_product_nt",
        "candidate_enzyme_programs",
        "recognition_placements_attempted",
        "constraint_systems_attempted",
        "nominal_combinations",
        "examined_combinations",
        "valid_realizations",
        "rejected_combinations",
        "distinct_geometry_groups",
        "distinct_final_products",
        "failure_reasons_json",
        "truncation_reasons",
        "upstream_truncation_reasons",
    )
    writer = _writer(buffer, fields)
    claims = projection.claim_boundary
    accounting = projection.accounting
    base = {
        "schema": projection.schema_id,
        "projection_id": projection.projection_id,
        "source_result_id": projection.source_result_id,
        "renderer_version": projection.renderer_version,
        "hop_version": projection.provenance.hop_version,
        "route_implementation_version": projection.provenance.route_implementation_version,
        "problem_id": projection.problem_id,
        "execution_id": projection.execution_id,
        "endpoint": projection.endpoint.value,
        "status": projection.status.value,
        "digital_design": claims.digital_design.value,
        "method": claims.method.value,
        "physical_construction": claims.physical_construction.value,
        "quality_control": claims.quality_control.value,
        "biological_activity": claims.biological_activity.value,
        "nominal_combinations": accounting.nominal_combinations,
        "examined_combinations": accounting.examined_combinations,
        "valid_realizations": accounting.valid_realizations,
        "rejected_combinations": accounting.rejected_combinations,
        "distinct_geometry_groups": accounting.distinct_geometry_groups,
        "distinct_final_products": accounting.distinct_final_products,
        "failure_reasons_json": json.dumps(
            [item.model_dump(mode="json") for item in projection.failure_reasons],
            sort_keys=True,
            separators=(",", ":"),
        ),
        "truncation_reasons": ";".join(projection.truncation_reasons),
        "upstream_truncation_reasons": ";".join(projection.upstream_truncation_reasons),
    }
    if not projection.rows:
        writer.writerow(base)
        return
    for row in projection.rows:
        writer.writerow(
            {
                **base,
                "ordinal": row.ordinal,
                "foldback_realization_id": row.foldback_realization_id,
                "basal_realization_id": row.basal_realization_id or "",
                "disposition": row.status.value,
                "rejection_reason": (
                    "" if row.rejection_reason is None else row.rejection_reason.value
                ),
                "truncation_reason": row.truncation_reason or "",
                "materialized_realization_id": row.materialized_realization_id or "",
                "achieved_geometry_group_key": row.achieved_geometry_group_key or "",
                "final_product_group_key": row.final_product_group_key or "",
                "material_ids": ";".join(row.material_ids),
                "route_material_dispositions_json": json.dumps(
                    [item.model_dump(mode="json") for item in row.route_material_dispositions],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "source_material_nt": row.source_material_nt,
                "auxiliary_material_nt": row.auxiliary_material_nt,
                "endpoint_product_nt": row.endpoint_product_nt,
                "candidate_enzyme_programs": row.candidate_enzyme_programs,
                "recognition_placements_attempted": row.recognition_placements_attempted,
                "constraint_systems_attempted": row.constraint_systems_attempted,
            }
        )


def _writer(buffer: io.StringIO, fields: tuple[str, ...]) -> csv.DictWriter[str]:
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    return writer


def _write_foldback(buffer: io.StringIO, projection: FoldbackFeasibilityProjection) -> None:
    fields = (
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "hop_version",
        "route_implementation_version",
        "endpoint",
        "completion",
        "feasibility",
        "termination_reason",
        *_partition_fields(projection),
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "local_realization_id",
        "foldback_realization_id",
        "program_kind",
        "nick_strand",
        "source_orientation",
        "junction_offset_nt",
        "loop_length_nt",
        "annealing_arm_length_bp",
        "retained_overhead_nt",
        "transient_construction_nt",
    )
    writer = _writer(buffer, fields)
    base = _base(projection)
    rows = projection.realizations or (None,)
    for row in rows:
        writer.writerow(
            {
                **base,
                **(row.model_dump(mode="json") if row is not None else {}),
            }
        )


def _write_basal(buffer: io.StringIO, projection: BasalFeasibilityProjection) -> None:
    fields = (
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "hop_version",
        "route_implementation_version",
        "endpoint",
        "completion",
        "feasibility",
        "termination_reason",
        *_partition_fields(projection),
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "local_realization_id",
        "basal_realization_id",
        "retained_overhead_nt",
        "nick_enzyme_id",
        "future_release_action_id",
        "future_release_enzyme_id",
        "nick_strand",
        "nick_offset_nt",
        "pairing_pattern",
        "pairing_classes",
        "literal_pairs_json",
        "proximal_annealing_nt",
        "required_annealing_nt",
        "annealing_completion_nt",
        "mismatch_fraction",
        "warnings",
    )
    writer = _writer(buffer, fields)
    base = _base(projection)
    rows = projection.realizations or (None,)
    for row in rows:
        values = row.model_dump(mode="json") if row is not None else {}
        if row is not None:
            values.pop("literal_pairs")
            values["pairing_classes"] = ";".join(item.value for item in row.pairing_classes)
            values["warnings"] = ";".join(row.warnings)
            values["literal_pairs_json"] = json.dumps(
                [item.model_dump(mode="json") for item in row.literal_pairs],
                sort_keys=True,
                separators=(",", ":"),
            )
        writer.writerow({**base, **values})


def _write_basal_matrix(
    buffer: io.StringIO,
    projection: BasalMinimumOverheadMatrixProjection,
) -> None:
    fields = (
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "hop_version",
        "route_implementation_version",
        "endpoint",
        "completion",
        "feasibility",
        "termination_reason",
        *_partition_fields(projection),
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "max_retained_overhead_nt",
        "nick_enzyme_id",
        "future_release_action_id",
        "future_release_enzyme_id",
        "future_release_orientation",
        "future_release_product_end",
        "future_release_overhang_end",
        "future_release_cohesive_end_sequence",
        "status",
        "minimum_retained_overhead_nt",
        "realization_count",
        "realization_ids",
    )
    writer = _writer(buffer, fields)
    base = _base(projection)
    action_by_id = {action.action_id: action for action in projection.release_actions}
    for cell in projection.cells:
        action = action_by_id[cell.future_release_action_id]
        writer.writerow(
            {
                **base,
                "max_retained_overhead_nt": projection.max_retained_overhead_nt,
                "nick_enzyme_id": cell.nick_enzyme_id,
                "future_release_action_id": action.action_id,
                "future_release_enzyme_id": action.enzyme_id,
                "future_release_orientation": action.requirement.orientation.value,
                "future_release_product_end": action.requirement.product_end,
                "future_release_overhang_end": action.requirement.overhang_end.value,
                "future_release_cohesive_end_sequence": (action.requirement.cohesive_end_sequence),
                "status": cell.status,
                "minimum_retained_overhead_nt": (
                    ""
                    if cell.minimum_retained_overhead_nt is None
                    else cell.minimum_retained_overhead_nt
                ),
                "realization_count": cell.realization_count,
                "realization_ids": ";".join(cell.realization_ids),
            }
        )


def _write_retained_overhead(
    buffer: io.StringIO,
    projection: RetainedOverheadFrontierProjection,
) -> None:
    fields = (
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "hop_version",
        "route_implementation_version",
        "family",
        "endpoint",
        "completion",
        "feasibility",
        "termination_reason",
        *_partition_fields(projection),
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "retained_overhead_nt",
        "level_status",
        "candidate_count",
        "realization_count",
        "rejected_count",
        "failure_reasons_json",
        "local_realization_id",
    )
    writer = _writer(buffer, fields)
    base = {
        **_base(projection),
        "family": projection.family,
    }
    for level in projection.levels:
        member_ids: tuple[str | None, ...] = level.realization_ids or (None,)
        for member_id in member_ids:
            writer.writerow(
                {
                    **base,
                    "retained_overhead_nt": level.retained_overhead_nt,
                    "level_status": level.status,
                    "candidate_count": level.candidate_count,
                    "realization_count": level.realization_count,
                    "rejected_count": level.rejected_count,
                    "failure_reasons_json": json.dumps(
                        [item.model_dump(mode="json") for item in level.failure_reasons],
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "local_realization_id": member_id or "",
                }
            )


def _base(projection: LocalScientificProjection) -> dict[str, object]:
    claims = projection.claim_boundary
    partition = projection.sequence_partition
    base: dict[str, object] = {
        "schema": projection.schema_id,
        "projection_id": projection.projection_id,
        "source_result_id": projection.source_result_id,
        "renderer_version": projection.renderer_version,
        "hop_version": projection.provenance.hop_version,
        "route_implementation_version": projection.provenance.route_implementation_version,
        "endpoint": projection.endpoint.value,
        "completion": projection.disposition.completion.value,
        "feasibility": projection.disposition.feasibility.value,
        "termination_reason": projection.disposition.termination_reason.value,
        "digital_design": claims.digital_design.value,
        "method": claims.method.value,
        "physical_construction": claims.physical_construction.value,
        "quality_control": claims.quality_control.value,
        "biological_activity": claims.biological_activity.value,
    }
    if partition is not None:
        base.update(
            sequence_part_count=partition.part_count,
            sequence_part_index=partition.part_index,
        )
    return base


def _partition_fields(projection: LocalScientificProjection) -> tuple[str, ...]:
    if projection.sequence_partition is None:
        return ()
    return ("sequence_part_count", "sequence_part_index")
