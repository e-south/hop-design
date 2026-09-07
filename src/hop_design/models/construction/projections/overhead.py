"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/overhead.py

Defines exact retained-overhead coverage projections for local construction search.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    FailureReasonCount,
    NeighborhoodClaimBoundary,
    NeighborhoodProvenance,
    SearchDisposition,
)
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.projection import ProjectionReference
from hop_design.models.construction.sequence_domain import SequenceDomainPartition

from .validation import validate_partition_schema, validate_projection_reference

FOLDBACK_OVERHEAD_RENDERER_VERSION = "foldback-overhead-projections/1"
FOLDBACK_PART_OVERHEAD_RENDERER_VERSION = "foldback-overhead-projections/2"


class RetainedOverheadLevelProjection(HopModel):
    """One examined retained-overhead level with exact realization membership."""

    retained_overhead_nt: int = Field(ge=0)
    status: Literal["complete", "partial"]
    candidate_count: int = Field(ge=0)
    realization_count: int = Field(ge=0)
    realization_ids: tuple[str, ...]
    rejected_count: int = Field(ge=0)
    failure_reasons: tuple[FailureReasonCount, ...]

    @model_validator(mode="after")
    def validate_membership(self) -> RetainedOverheadLevelProjection:
        if self.realization_count != len(self.realization_ids):
            raise ValueError("Overhead-level count must equal exact membership.")
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("Overhead-level membership must not repeat a realization.")
        if self.candidate_count != self.realization_count + self.rejected_count:
            raise ValueError("Overhead-level candidates must equal accepted plus rejected.")
        codes = tuple(item.code for item in self.failure_reasons)
        if len(codes) != len(set(codes)):
            raise ValueError("Overhead-level failure reasons must be unique.")
        if sum(item.count for item in self.failure_reasons) != self.rejected_count:
            raise ValueError("Overhead-level failures must partition rejected candidates.")
        return self


class RetainedOverheadFrontierProjection(HopModel):
    """Absolute retained-overhead coverage with exact realization membership."""

    schema_id: Literal[
        "hop.foldback-overhead-frontier/v1",
        "hop.foldback-overhead-frontier/v2",
        "hop.basal-overhead-frontier/v1",
        "hop.basal-overhead-frontier/v2",
    ] = Field(alias="schema")
    projection_reference: ProjectionReference
    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    source_result_id: str = Field(
        pattern=(
            r"^hop:(?:foldback-neighborhood-result|basal-neighborhood-result)/"
            r"[0-9a-f]{64}@1$"
        )
    )
    renderer_version: str
    provenance: NeighborhoodProvenance
    claim_boundary: NeighborhoodClaimBoundary
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    family: Literal["foldback", "basal"]
    endpoint: ConstructionEndpoint
    disposition: SearchDisposition
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    levels: tuple[RetainedOverheadLevelProjection, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_projection(self) -> RetainedOverheadFrontierProjection:
        if self.family == "foldback":
            validate_partition_schema(
                schema_id=self.schema_id,
                sequence_partition=self.sequence_partition,
                unpartitioned_schema="hop.foldback-overhead-frontier/v1",
                partitioned_schema="hop.foldback-overhead-frontier/v2",
            )
        else:
            validate_partition_schema(
                schema_id=self.schema_id,
                sequence_partition=self.sequence_partition,
                unpartitioned_schema="hop.basal-overhead-frontier/v1",
                partitioned_schema="hop.basal-overhead-frontier/v2",
            )
        overheads = tuple(level.retained_overhead_nt for level in self.levels)
        if overheads != tuple(range(len(overheads))):
            raise ValueError("Overhead-frontier levels must be contiguous from zero.")
        partial_levels = tuple(
            index for index, level in enumerate(self.levels) if level.status == "partial"
        )
        if partial_levels and partial_levels != (len(self.levels) - 1,):
            raise ValueError("Only the final overhead level may be partial.")
        if self.disposition.completion == "complete" and partial_levels:
            raise ValueError("Complete overhead coverage cannot contain a partial level.")
        member_ids = tuple(item for level in self.levels for item in level.realization_ids)
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("Overhead-frontier levels must partition exact membership.")
        validate_projection_reference(
            schema_id=self.schema_id,
            reference=self.projection_reference,
            projection_id=self.projection_id,
            source_result_id=self.source_result_id,
            renderer_version=self.renderer_version,
            realization_ids=member_ids,
        )
        return self
