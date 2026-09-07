"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/validation.py

Validates shared identity, coverage, and partition contracts for local projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.accounting import SearchDisposition
from hop_design.models.construction.projection import ProjectionReference
from hop_design.models.construction.sequence_domain import SequenceDomainPartition


def validate_partition_schema(
    *,
    schema_id: str,
    sequence_partition: SequenceDomainPartition | None,
    unpartitioned_schema: str,
    partitioned_schema: str,
) -> None:
    """Require the schema version to disclose whether the result is partitioned."""
    expected = partitioned_schema if sequence_partition is not None else unpartitioned_schema
    if schema_id != expected:
        raise ValueError("Projection schema must match its sequence-domain scope.")


def validate_feasibility_disposition(
    *,
    disposition: SearchDisposition,
    realization_count: int,
    row_count: int,
    ids: tuple[str, ...],
) -> None:
    """Require exact rows and feasibility status to agree."""
    if realization_count != row_count:
        raise ValueError("Feasibility count must equal exact realization rows.")
    if len(ids) != len(set(ids)):
        raise ValueError("Feasibility rows must not repeat a local realization.")
    if disposition.feasibility == "infeasible" and realization_count:
        raise ValueError("Infeasible projections cannot contain realizations.")
    if disposition.feasibility == "feasible" and not realization_count:
        raise ValueError("Feasible projections require at least one realization.")


def validate_projection_reference(
    *,
    schema_id: str,
    reference: ProjectionReference,
    projection_id: str,
    source_result_id: str,
    renderer_version: str,
    realization_ids: tuple[str, ...],
) -> None:
    """Replay projection identity and exact realization membership."""
    if reference.projection_schema != schema_id:
        raise ValueError("Projection reference schema must match the typed projection.")
    if reference.realization_ids != realization_ids:
        raise ValueError("Projection reference must preserve every source realization in order.")
    if (
        projection_id != reference.projection_id
        or source_result_id != reference.result_id
        or renderer_version != reference.renderer_version
    ):
        raise ValueError("Projection identity fields must replay the shared projection reference.")
