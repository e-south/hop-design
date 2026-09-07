"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/source_partition.py

Defines an exact, renderer-independent source-partition certificate projection.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, Literal, Self, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    DigitalDesignStatus,
    ExperimentalEvidenceStatus,
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
    SearchCompletionStatus,
)
from hop_design.models.construction.payload import _content_id
from hop_design.models.construction.source_partition import SourcePartitionCertificate

SOURCE_PARTITION_CERTIFICATE_RENDERER_VERSION: Literal["source-partition-certificate/1"] = (
    "source-partition-certificate/1"
)


class SourcePartitionCertificateProjection(HopModel):
    """One selected full-span partition certificate for scientific inspection."""

    schema_id: Literal["hop.source-partition-certificate/v1"] = Field(
        default="hop.source-partition-certificate/v1",
        alias="schema",
    )
    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:source-partition-result/[0-9a-f]{64}@1$")
    renderer_version: Literal["source-partition-certificate/1"] = (
        SOURCE_PARTITION_CERTIFICATE_RENDERER_VERSION
    )
    problem_id: str = Field(pattern=r"^hop:source-partition-problem/[0-9a-f]{64}@1$")
    status: SearchCompletionStatus
    candidate_space_size: int = Field(ge=1)
    examined_nodes: int = Field(ge=1)
    realization_id: str = Field(pattern=r"^hop:source-partition-realization/[0-9a-f]{64}@1$")
    enzyme_ids: tuple[str, ...] = Field(min_length=1)
    certificate: SourcePartitionCertificate
    claim_boundary: NeighborhoodClaimBoundary

    @classmethod
    def create(cls, **content: object) -> Self:
        """Seal one projection over already verified source-partition content."""
        draft = cls.model_construct(projection_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", by_alias=True, exclude={"projection_id"})
        return cls.model_validate(
            {
                **content,
                "projection_id": _content_id("projection", 1, seed),
            }
        )

    @model_validator(mode="after")
    def validate_projection(self) -> Self:
        if self.status is SearchCompletionStatus.INFEASIBLE:
            raise ValueError("An infeasible partition result cannot have a certificate projection.")
        if self.examined_nodes > self.candidate_space_size:
            raise ValueError("Examined partition nodes cannot exceed the candidate space.")
        if self.enzyme_ids != tuple(sorted(set(self.enzyme_ids))):
            raise ValueError("Projected source-partition enzymes must be unique and canonical.")
        boundary_enzymes = {
            enzyme_id
            for fragment in self.certificate.fragments
            for boundary in (fragment.left_boundary, fragment.right_boundary)
            for enzyme_id in boundary.enzyme_ids
        }
        if boundary_enzymes != set(self.enzyme_ids):
            raise ValueError("Projected enzymes must equal the fragment-boundary causes.")
        expected_boundary = NeighborhoodClaimBoundary(
            digital_design=DigitalDesignStatus.VERIFIED,
            method=MethodResolutionStatus.NOT_RESOLVED,
            physical_construction=ExperimentalEvidenceStatus.NOT_RECORDED,
            quality_control=ExperimentalEvidenceStatus.NOT_RECORDED,
            biological_activity=ExperimentalEvidenceStatus.NOT_RECORDED,
        )
        if self.claim_boundary != expected_boundary:
            raise ValueError("Source-partition claim boundaries are fixed by result scope.")
        seed = self.model_dump(mode="json", by_alias=True, exclude={"projection_id"})
        if self.projection_id != _content_id("projection", 1, seed):
            raise ValueError("Source-partition projection identity must replay exact content.")
        return self


__all__ = [
    "SOURCE_PARTITION_CERTIFICATE_RENDERER_VERSION",
    "SourcePartitionCertificateProjection",
]
