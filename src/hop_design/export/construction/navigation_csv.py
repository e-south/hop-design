"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/navigation_csv.py

Serializes accepted construction routes as deterministic tidy CSV.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json

from hop_design.models.base import HopModel
from hop_design.models.construction.projections import ConstructionNavigationProjection


def render_navigation_projection_csv(
    projection: ConstructionNavigationProjection,
) -> bytes:
    """Render accepted routes with their canonical summary-row context."""
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
        "result_status",
        "ordinal",
        "foldback_realization_id",
        "basal_realization_id",
        "materialized_realization_id",
        "achieved_geometry_group_key",
        "final_product_group_key",
        "foldback_geometry",
        "basal_geometry",
        "foldback_retained_overhead_nt",
        "basal_retained_overhead_nt",
        "cleavage_enzyme_ids",
        "retained_non_payload_nt",
        "final_product_topology",
        "material_ids",
        "required_external_material_count",
        "route_material_dispositions_json",
        "source_material_nt",
        "auxiliary_material_nt",
        "endpoint_product_nt",
    )
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()

    summary = projection.summary
    summary_rows = {
        row.materialized_realization_id: row
        for row in summary.rows
        if row.materialized_realization_id is not None
    }
    base = {
        "schema": projection.schema_id,
        "projection_id": projection.projection_id,
        "source_result_id": projection.source_result_id,
        "renderer_version": projection.renderer_version,
        "hop_version": summary.provenance.hop_version,
        "route_implementation_version": summary.provenance.route_implementation_version,
        "problem_id": summary.problem_id,
        "execution_id": summary.execution_id,
        "endpoint": summary.endpoint.value,
        "result_status": summary.status.value,
    }
    for route in projection.accepted_routes:
        row = summary_rows[route.materialized_realization_id]
        writer.writerow(
            {
                **base,
                "ordinal": row.ordinal,
                "foldback_realization_id": row.foldback_realization_id,
                "basal_realization_id": row.basal_realization_id or "",
                "materialized_realization_id": route.materialized_realization_id,
                "achieved_geometry_group_key": row.achieved_geometry_group_key or "",
                "final_product_group_key": row.final_product_group_key or "",
                "foldback_geometry": _json_model(route.foldback_geometry),
                "basal_geometry": _json_model(route.basal_geometry),
                "foldback_retained_overhead_nt": route.foldback_retained_overhead_nt,
                "basal_retained_overhead_nt": _optional(route.basal_retained_overhead_nt),
                "cleavage_enzyme_ids": ";".join(route.cleavage_enzyme_ids),
                "retained_non_payload_nt": route.retained_non_payload_nt,
                "final_product_topology": route.final_product_topology,
                "material_ids": ";".join(row.material_ids),
                "required_external_material_count": len(row.material_ids),
                "route_material_dispositions_json": json.dumps(
                    [item.model_dump(mode="json") for item in row.route_material_dispositions],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "source_material_nt": row.source_material_nt,
                "auxiliary_material_nt": row.auxiliary_material_nt,
                "endpoint_product_nt": row.endpoint_product_nt,
            }
        )
    return buffer.getvalue().encode("utf-8")


def _json_model(value: HopModel | None) -> str:
    if value is None:
        return ""
    return json.dumps(
        value.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def _optional(value: object | None) -> object:
    return "" if value is None else value


__all__ = ["render_navigation_projection_csv"]
