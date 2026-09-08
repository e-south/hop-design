"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/complete_csv.py

Writes complete-construction summary projections as deterministic tidy CSV.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import io
import json

from hop_design.models.construction.projections import CompleteConstructionSummaryProjection

from .csv_common import writer


def write_complete_projection(
    buffer: io.StringIO,
    projection: CompleteConstructionSummaryProjection,
) -> None:
    """Write one complete-construction summary relation."""
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
        "source_context_sequence",
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
    table = writer(buffer, fields)
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
        table.writerow(base)
        return
    for row in projection.rows:
        table.writerow(
            {
                **base,
                "ordinal": row.ordinal,
                "source_context_sequence": row.source_context_sequence or "",
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
