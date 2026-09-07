"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/csv_common.py

Provides shared deterministic CSV fields for local construction projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io

from hop_design.models.construction.projections import LocalScientificProjection


def writer(buffer: io.StringIO, fields: tuple[str, ...]) -> csv.DictWriter[str]:
    """Create a deterministic dictionary writer and emit its header."""
    table = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    table.writeheader()
    return table


def local_base(projection: LocalScientificProjection) -> dict[str, object]:
    """Return repeated authority and claim fields for a local projection row."""
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


def partition_fields(projection: LocalScientificProjection) -> tuple[str, ...]:
    """Return explicit sequence-part columns when the search was partitioned."""
    if projection.sequence_partition is None:
        return ()
    return ("sequence_part_count", "sequence_part_index")
