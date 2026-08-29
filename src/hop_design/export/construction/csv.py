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
    FoldbackFeasibilityProjection,
    LocalScientificProjection,
    RelaxationFrontierProjection,
)


def render_projection_csv(projection: LocalScientificProjection) -> bytes:
    """Render one projection with repeated context and lossless exact membership."""
    buffer = io.StringIO(newline="")
    if isinstance(projection, FoldbackFeasibilityProjection):
        _write_foldback(buffer, projection)
    elif isinstance(projection, BasalFeasibilityProjection):
        _write_basal(buffer, projection)
    elif isinstance(projection, RelaxationFrontierProjection):
        _write_relaxation(buffer, projection)
    else:  # pragma: no cover - strict union protects public callers
        raise TypeError(f"Unsupported scientific projection: {type(projection).__name__}")
    return buffer.getvalue().encode("utf-8")


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
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "local_realization_id",
        "foldback_realization_id",
        "program_kind",
        "relaxation_radius",
        "junction_offset_nt",
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
        "type_iis_cut_offset_nt",
        "pairing_profile",
        "pairing_classes",
        "literal_pairs_json",
        "retained_nt",
        "transient_nt",
        "auxiliary_nt",
        "cohesive_end_count",
        "cohesive_ends_json",
        "truncation_reasons",
    )
    writer = _writer(buffer, fields)
    base = _base(projection)
    rows = projection.realizations or (None,)
    for row in rows:
        values = row.model_dump(mode="json") if row is not None else {}
        if row is not None:
            values.pop("literal_pairs")
            values.pop("cohesive_ends")
            values["pairing_classes"] = ";".join(item.value for item in row.pairing_classes)
            values["literal_pairs_json"] = json.dumps(
                [item.model_dump(mode="json") for item in row.literal_pairs],
                sort_keys=True,
                separators=(",", ":"),
            )
            values["cohesive_ends_json"] = json.dumps(
                [item.model_dump(mode="json") for item in row.cohesive_ends],
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
    return {
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
