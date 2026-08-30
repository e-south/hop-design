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
    CompleteConstructionSummaryProjection,
    FoldbackFeasibilityProjection,
    LocalScientificProjection,
    RelaxationFrontierProjection,
)


def render_projection_csv(
    projection: LocalScientificProjection | CompleteConstructionSummaryProjection,
) -> bytes:
    """Render one projection with repeated context and lossless exact membership."""
    buffer = io.StringIO(newline="")
    if isinstance(projection, CompleteConstructionSummaryProjection):
        _write_complete(buffer, projection)
    elif isinstance(projection, FoldbackFeasibilityProjection):
        _write_foldback(buffer, projection)
    elif isinstance(projection, BasalFeasibilityProjection):
        _write_basal(buffer, projection)
    elif isinstance(projection, RelaxationFrontierProjection):
        _write_relaxation(buffer, projection)
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
        "status",
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
        "relaxation_radius",
        "nick_offset_within_foldback_nt",
        "loop_length_nt",
        "annealing_arm_length_bp",
        "retained_construction_nt",
        "transient_construction_nt",
        "truncation_reasons",
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
        "status",
        *_partition_fields(projection),
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "local_realization_id",
        "basal_realization_id",
        "relaxation_radius",
        "nick_strand",
        "nick_offset_nt",
        "pairing_profile",
        "pairing_classes",
        "literal_pairs_json",
        "retained_nt",
        "transient_nt",
        "auxiliary_nt",
        "truncation_reasons",
    )
    writer = _writer(buffer, fields)
    base = _base(projection)
    rows = projection.realizations or (None,)
    for row in rows:
        values = row.model_dump(mode="json") if row is not None else {}
        if row is not None:
            values.pop("literal_pairs")
            values["pairing_classes"] = ";".join(item.value for item in row.pairing_classes)
            values["literal_pairs_json"] = json.dumps(
                [item.model_dump(mode="json") for item in row.literal_pairs],
                sort_keys=True,
                separators=(",", ":"),
            )
        writer.writerow({**base, **values})


def _write_relaxation(buffer: io.StringIO, projection: RelaxationFrontierProjection) -> None:
    fields = (
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "hop_version",
        "route_implementation_version",
        "family",
        "endpoint",
        "status",
        *_partition_fields(projection),
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "coordinate_names",
        "radius",
        "shell_status",
        "candidate_count",
        "realization_count",
        "rejected_count",
        "failure_reasons_json",
        "local_realization_id",
        "truncation_reasons",
    )
    writer = _writer(buffer, fields)
    base = {
        **_base(projection),
        "family": projection.family,
        "coordinate_names": ";".join(projection.coordinate_names),
    }
    for shell in projection.shells:
        member_ids: tuple[str | None, ...] = shell.realization_ids or (None,)
        for member_id in member_ids:
            writer.writerow(
                {
                    **base,
                    "radius": shell.radius,
                    "shell_status": shell.status,
                    "candidate_count": shell.candidate_count,
                    "realization_count": shell.realization_count,
                    "rejected_count": shell.rejected_count,
                    "failure_reasons_json": json.dumps(
                        [item.model_dump(mode="json") for item in shell.failure_reasons],
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
        "status": projection.status.value,
        "digital_design": claims.digital_design.value,
        "method": claims.method.value,
        "physical_construction": claims.physical_construction.value,
        "quality_control": claims.quality_control.value,
        "biological_activity": claims.biological_activity.value,
        "truncation_reasons": ";".join(projection.truncation_reasons),
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
