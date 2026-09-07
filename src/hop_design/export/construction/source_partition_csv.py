"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/source_partition_csv.py

Serializes one source-partition certificate as a tidy fragment relation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json

from hop_design.models.construction.projections import SourcePartitionCertificateProjection


def render_source_partition_projection_csv(
    projection: SourcePartitionCertificateProjection,
) -> bytes:
    """Render exact fragment and boundary facts with repeated projection context."""
    fields = (
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "problem_id",
        "status",
        "candidate_space_size",
        "examined_nodes",
        "realization_id",
        "enzyme_ids",
        "selected_maximum_sacrificial_fragment_nt",
        "thresholds_json",
        "digital_design",
        "method",
        "physical_construction",
        "quality_control",
        "biological_activity",
        "fragment_id",
        "strand",
        "source_start",
        "source_end",
        "length_nt",
        "disposition",
        "survivor_id",
        "left_boundary_kind",
        "left_physical_end",
        "left_enzyme_ids",
        "right_boundary_kind",
        "right_physical_end",
        "right_enzyme_ids",
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    certificate = projection.certificate
    claims = projection.claim_boundary
    base = {
        "schema": projection.schema_id,
        "projection_id": projection.projection_id,
        "source_result_id": projection.source_result_id,
        "renderer_version": projection.renderer_version,
        "problem_id": projection.problem_id,
        "status": projection.status.value,
        "candidate_space_size": projection.candidate_space_size,
        "examined_nodes": projection.examined_nodes,
        "realization_id": projection.realization_id,
        "enzyme_ids": ";".join(projection.enzyme_ids),
        "selected_maximum_sacrificial_fragment_nt": (
            certificate.selected_maximum_sacrificial_fragment_nt
        ),
        "thresholds_json": json.dumps(
            [item.model_dump(mode="json") for item in certificate.thresholds],
            sort_keys=True,
            separators=(",", ":"),
        ),
        "digital_design": claims.digital_design.value,
        "method": claims.method.value,
        "physical_construction": claims.physical_construction.value,
        "quality_control": claims.quality_control.value,
        "biological_activity": claims.biological_activity.value,
    }
    for fragment in certificate.fragments:
        writer.writerow(
            {
                **base,
                "fragment_id": fragment.fragment_id,
                "strand": fragment.precursor_strand.value,
                "source_start": fragment.source_span.start.offset,
                "source_end": fragment.source_span.end.offset,
                "length_nt": fragment.length_nt,
                "disposition": fragment.disposition.value,
                "survivor_id": fragment.survivor_id or "",
                "left_boundary_kind": fragment.left_boundary.kind.value,
                "left_physical_end": (
                    ""
                    if fragment.left_boundary.physical_end is None
                    else fragment.left_boundary.physical_end.value
                ),
                "left_enzyme_ids": ";".join(fragment.left_boundary.enzyme_ids),
                "right_boundary_kind": fragment.right_boundary.kind.value,
                "right_physical_end": (
                    ""
                    if fragment.right_boundary.physical_end is None
                    else fragment.right_boundary.physical_end.value
                ),
                "right_enzyme_ids": ";".join(fragment.right_boundary.enzyme_ids),
            }
        )
    return output.getvalue().encode("utf-8")


__all__ = ["render_source_partition_projection_csv"]
