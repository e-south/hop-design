"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/local_csv.py

Writes local-neighborhood and overhead projections as deterministic tidy CSV.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import io
import json

from hop_design.models.construction.projections import (
    BasalFeasibilityProjection,
    BasalMinimumOverheadMatrixProjection,
    FoldbackFeasibilityProjection,
    RetainedOverheadFrontierProjection,
)

from .csv_common import local_base, partition_fields, writer

_LOCAL_FIELDS = (
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
)
_CLAIM_FIELDS = (
    "digital_design",
    "method",
    "physical_construction",
    "quality_control",
    "biological_activity",
)


def write_foldback_projection(
    buffer: io.StringIO,
    projection: FoldbackFeasibilityProjection,
) -> None:
    """Write every exact foldback realization."""
    fields = (
        *_LOCAL_FIELDS,
        *partition_fields(projection),
        *_CLAIM_FIELDS,
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
    table = writer(buffer, fields)
    base = local_base(projection)
    rows = projection.realizations or (None,)
    for row in rows:
        table.writerow({**base, **(row.model_dump(mode="json") if row is not None else {})})


def write_basal_projection(
    buffer: io.StringIO,
    projection: BasalFeasibilityProjection,
) -> None:
    """Write every exact basal realization and annealing obligation."""
    fields = (
        *_LOCAL_FIELDS,
        *partition_fields(projection),
        *_CLAIM_FIELDS,
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
    table = writer(buffer, fields)
    base = local_base(projection)
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
        table.writerow({**base, **values})


def write_basal_matrix_projection(
    buffer: io.StringIO,
    projection: BasalMinimumOverheadMatrixProjection,
) -> None:
    """Write every nickase and future-release matrix cell."""
    fields = (
        *_LOCAL_FIELDS,
        *partition_fields(projection),
        *_CLAIM_FIELDS,
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
    table = writer(buffer, fields)
    base = local_base(projection)
    action_by_id = {action.action_id: action for action in projection.release_actions}
    for cell in projection.cells:
        action = action_by_id[cell.future_release_action_id]
        table.writerow(
            {
                **base,
                "max_retained_overhead_nt": projection.max_retained_overhead_nt,
                "nick_enzyme_id": cell.nick_enzyme_id,
                "future_release_action_id": action.action_id,
                "future_release_enzyme_id": action.enzyme_id,
                "future_release_orientation": action.requirement.orientation.value,
                "future_release_product_end": action.requirement.product_end,
                "future_release_overhang_end": action.requirement.overhang_end.value,
                "future_release_cohesive_end_sequence": action.requirement.cohesive_end_sequence,
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


def write_retained_overhead_projection(
    buffer: io.StringIO,
    projection: RetainedOverheadFrontierProjection,
) -> None:
    """Write every overhead level and exact realization membership."""
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
        *partition_fields(projection),
        *_CLAIM_FIELDS,
        "retained_overhead_nt",
        "level_status",
        "candidate_count",
        "realization_count",
        "rejected_count",
        "failure_reasons_json",
        "local_realization_id",
    )
    table = writer(buffer, fields)
    base = {**local_base(projection), "family": projection.family}
    for level in projection.levels:
        member_ids: tuple[str | None, ...] = level.realization_ids or (None,)
        for member_id in member_ids:
            table.writerow(
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
