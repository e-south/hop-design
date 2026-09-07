"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/trajectory.py

Builds and verifies one selected complete-construction trajectory.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.design.construction.complete.discovery import VerifiedConstructionSpaceResult
from hop_design.models.construction.complete import CompositionDispositionStatus
from hop_design.models.construction.projections import (
    CompleteConstructionTrajectoryProjection,
)
from hop_design.serialization import canonical_json_bytes

from .complete import _admit_source


def project_complete_construction_trajectory(
    source: VerifiedConstructionSpaceResult,
    *,
    materialized_realization_id: str,
) -> CompleteConstructionTrajectoryProjection:
    """Project exactly one caller-selected accepted route from a verified source."""
    admitted = _admit_source(source)
    result = admitted.result
    realizations = {item.materialized_realization_id: item for item in result.realizations}
    realization = realizations.get(materialized_realization_id)
    if realization is None:
        rejected_ids = {
            identifier
            for item in result.combination_dispositions
            if item.status is CompositionDispositionStatus.REJECTED
            for identifier in (item.foldback_realization_id, item.basal_realization_id)
            if identifier is not None
        }
        if materialized_realization_id in rejected_ids:
            raise ValueError("Rejected construction compositions have no trajectory projection.")
        raise ValueError(
            f"Unknown accepted materialized construction realization: {materialized_realization_id}"
        )
    disposition = next(
        item
        for item in result.combination_dispositions
        if item.materialized_realization_id == materialized_realization_id
    )
    source_partition_certificate = None
    if realization.source_partition_binding is not None:
        authority = result.source_partition_authority
        if authority is None:
            raise ValueError("A selected source-partition binding requires its source authority.")
        selected_partition = next(
            (
                item
                for item in authority.realizations
                if item.realization_id == realization.source_partition_binding.realization_id
            ),
            None,
        )
        if selected_partition is None:
            raise ValueError(
                "A selected source-partition binding must resolve inside its source authority."
            )
        source_partition_certificate = selected_partition.fragment_certificate
    return CompleteConstructionTrajectoryProjection.create(
        source_result_id=result.result_id,
        composition_ordinal=disposition.ordinal,
        realization=realization,
        source_partition_certificate=source_partition_certificate,
    )


def verify_complete_construction_trajectory(
    projection: CompleteConstructionTrajectoryProjection,
    source: VerifiedConstructionSpaceResult,
) -> CompleteConstructionTrajectoryProjection:
    """Require canonical equality with the selected route in its verified source."""
    parsed = CompleteConstructionTrajectoryProjection.model_validate(
        projection.model_dump(mode="python", by_alias=True)
    )
    expected = project_complete_construction_trajectory(
        source,
        materialized_realization_id=parsed.realization.materialized_realization_id,
    )
    if canonical_json_bytes(parsed) != canonical_json_bytes(expected):
        raise ValueError(
            "Complete construction trajectory does not replay its verified source result."
        )
    return parsed


__all__ = [
    "project_complete_construction_trajectory",
    "verify_complete_construction_trajectory",
]
