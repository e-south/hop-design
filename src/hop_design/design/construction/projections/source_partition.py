"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projections/source_partition.py

Builds exact source-partition projections from replay-verified results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.accounting import (
    DigitalDesignStatus,
    ExperimentalEvidenceStatus,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
)
from hop_design.models.construction.projections import SourcePartitionCertificateProjection
from hop_design.models.construction.source_partition import SourcePartitionDiscoveryResult


def project_source_partition_certificate(
    result: SourcePartitionDiscoveryResult,
    *,
    realization_id: str,
) -> SourcePartitionCertificateProjection:
    """Project one explicitly selected accepted source-partition realization."""
    verified = SourcePartitionDiscoveryResult.model_validate(
        result.model_dump(mode="python", by_alias=True)
    )
    realization = next(
        (item for item in verified.realizations if item.realization_id == realization_id),
        None,
    )
    if realization is None:
        raise ValueError("The realization is not present in the verified source partition.")
    return SourcePartitionCertificateProjection.create(
        source_result_id=verified.result_id,
        problem_id=verified.problem_id,
        status=verified.status,
        candidate_space_size=verified.candidate_space_size,
        examined_nodes=verified.examined_nodes,
        realization_id=realization.realization_id,
        enzyme_ids=realization.enzyme_ids,
        certificate=realization.fragment_certificate,
        claim_boundary=NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
            physical_construction=ExperimentalEvidenceStatus.NOT_RECORDED,
            quality_control=ExperimentalEvidenceStatus.NOT_RECORDED,
            biological_activity=ExperimentalEvidenceStatus.NOT_RECORDED,
        ),
    )


def verify_source_partition_projection(
    projection: SourcePartitionCertificateProjection,
    source: SourcePartitionDiscoveryResult,
) -> SourcePartitionCertificateProjection:
    """Replay one certificate projection against its detailed source result."""
    expected = project_source_partition_certificate(
        source,
        realization_id=projection.realization_id,
    )
    if projection != expected:
        raise ValueError("Source-partition projection does not replay its source result.")
    return projection


__all__ = [
    "project_source_partition_certificate",
    "verify_source_partition_projection",
]
