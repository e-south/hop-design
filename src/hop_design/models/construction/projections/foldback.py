"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/foldback.py

Defines lossless scientific projections of foldback-neighborhood discovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    NeighborhoodClaimBoundary,
    NeighborhoodProvenance,
    SearchDisposition,
)
from hop_design.models.construction.foldback.binding import FoldbackCleavageProgramKind
from hop_design.models.construction.payload import ConstructionEndpoint, SourceOrientation
from hop_design.models.construction.projection import ProjectionReference
from hop_design.models.construction.sequence_domain import SequenceDomainPartition
from hop_design.models.junction import Strand

from .validation import (
    validate_feasibility_disposition,
    validate_partition_schema,
    validate_projection_reference,
)

FOLDBACK_FEASIBILITY_RENDERER_VERSION = "foldback-feasibility-projections/3"
FOLDBACK_PART_FEASIBILITY_RENDERER_VERSION = "foldback-feasibility-projections/4"


class FoldbackFeasibilityRow(HopModel):
    """One exact foldback realization and its observed construction dimensions."""

    local_realization_id: str = Field(pattern=r"^hop:local-realization/[0-9a-f]{64}@1$")
    foldback_realization_id: str = Field(pattern=r"^hop:foldback-realization/[0-9a-f]{64}@1$")
    program_kind: FoldbackCleavageProgramKind
    nick_strand: Strand
    source_orientation: SourceOrientation
    junction_offset_nt: int = Field(ge=0)
    loop_length_nt: int = Field(ge=1)
    annealing_arm_length_bp: int = Field(ge=1)
    retained_overhead_nt: int = Field(ge=0)
    transient_construction_nt: int = Field(ge=0)


class FoldbackFeasibilityProjection(HopModel):
    """Neutral foldback feasibility relation over exact realization authorities."""

    schema_id: Literal[
        "hop.foldback-feasibility-landscape/v3",
        "hop.foldback-feasibility-landscape/v4",
    ] = Field(default="hop.foldback-feasibility-landscape/v3", alias="schema")
    projection_reference: ProjectionReference
    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:foldback-neighborhood-result/[0-9a-f]{64}@1$")
    renderer_version: str
    provenance: NeighborhoodProvenance
    claim_boundary: NeighborhoodClaimBoundary
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    endpoint: ConstructionEndpoint
    disposition: SearchDisposition
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    realization_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    realizations: tuple[FoldbackFeasibilityRow, ...]

    @model_validator(mode="after")
    def validate_projection(self) -> FoldbackFeasibilityProjection:
        validate_partition_schema(
            schema_id=self.schema_id,
            sequence_partition=self.sequence_partition,
            unpartitioned_schema="hop.foldback-feasibility-landscape/v3",
            partitioned_schema="hop.foldback-feasibility-landscape/v4",
        )
        validate_feasibility_disposition(
            disposition=self.disposition,
            realization_count=self.realization_count,
            row_count=len(self.realizations),
            ids=tuple(row.local_realization_id for row in self.realizations),
        )
        validate_projection_reference(
            schema_id=self.schema_id,
            reference=self.projection_reference,
            projection_id=self.projection_id,
            source_result_id=self.source_result_id,
            renderer_version=self.renderer_version,
            realization_ids=tuple(row.local_realization_id for row in self.realizations),
        )
        return self
