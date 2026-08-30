"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/local.py

Defines lossless scientific projections of local construction discovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    FailureReasonCount,
    NeighborhoodClaimBoundary,
    NeighborhoodProvenance,
    SearchCompletionStatus,
)
from hop_design.models.construction.basal.pairing import BasalPairRecord
from hop_design.models.construction.foldback.binding import FoldbackCleavageProgramKind
from hop_design.models.construction.payload import ConstructionEndpoint, SourceOrientation
from hop_design.models.construction.projection import ProjectionReference
from hop_design.models.construction.relaxation import SequenceDomainPartition
from hop_design.models.construction.targets import BasalPairClass
from hop_design.models.junction import Strand

FOLDBACK_FEASIBILITY_RENDERER_VERSION = "foldback-feasibility-projections/3"
FOLDBACK_PART_FEASIBILITY_RENDERER_VERSION = "foldback-feasibility-projections/4"
FOLDBACK_RELAXATION_RENDERER_VERSION = "foldback-projections/2"
FOLDBACK_PART_RELAXATION_RENDERER_VERSION = "foldback-projections/3"
BASAL_PROJECTION_RENDERER_VERSION = "basal-projections/2"
BASAL_PART_PROJECTION_RENDERER_VERSION = "basal-projections/3"


class FoldbackFeasibilityRow(HopModel):
    """One exact foldback realization and its observed construction dimensions."""

    local_realization_id: str = Field(pattern=r"^hop:local-realization/[0-9a-f]{64}@1$")
    foldback_realization_id: str = Field(pattern=r"^hop:foldback-realization/[0-9a-f]{64}@1$")
    program_kind: FoldbackCleavageProgramKind
    nick_strand: Strand
    source_orientation: SourceOrientation
    relaxation_radius: int = Field(ge=0)
    nick_offset_within_foldback_nt: int = Field(ge=0)
    loop_length_nt: int = Field(ge=1)
    annealing_arm_length_bp: int = Field(ge=1)
    retained_construction_nt: int = Field(ge=0)
    transient_construction_nt: int = Field(ge=0)


class BasalFeasibilityRow(HopModel):
    """One exact basal realization and its PCR-intermediate material dimensions."""

    local_realization_id: str = Field(pattern=r"^hop:local-realization/[0-9a-f]{64}@1$")
    basal_realization_id: str = Field(pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$")
    relaxation_radius: int = Field(ge=0)
    nick_strand: Strand
    nick_offset_nt: int = Field(ge=0)
    pairing_profile: str | None
    pairing_classes: tuple[BasalPairClass, ...]
    literal_pairs: tuple[BasalPairRecord, ...]
    retained_nt: int = Field(ge=0)
    transient_nt: int = Field(ge=0)
    auxiliary_nt: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_exact_details(self) -> BasalFeasibilityRow:
        if self.pairing_classes != tuple(item.pair_class for item in self.literal_pairs):
            raise ValueError("Basal pairing classes must replay every literal pair.")
        return self


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
    status: SearchCompletionStatus
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    realization_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    truncation_reasons: tuple[str, ...]
    realizations: tuple[FoldbackFeasibilityRow, ...]

    @model_validator(mode="after")
    def validate_projection(self) -> FoldbackFeasibilityProjection:
        _validate_partition_schema(
            schema_id=self.schema_id,
            sequence_partition=self.sequence_partition,
            unpartitioned_schema="hop.foldback-feasibility-landscape/v3",
            partitioned_schema="hop.foldback-feasibility-landscape/v4",
        )
        _validate_feasibility_status(
            status=self.status,
            realization_count=self.realization_count,
            row_count=len(self.realizations),
            ids=tuple(row.local_realization_id for row in self.realizations),
            truncation_reasons=self.truncation_reasons,
        )
        _validate_projection_reference(
            schema_id=self.schema_id,
            reference=self.projection_reference,
            projection_id=self.projection_id,
            source_result_id=self.source_result_id,
            renderer_version=self.renderer_version,
            realization_ids=tuple(row.local_realization_id for row in self.realizations),
        )
        return self


class BasalFeasibilityProjection(HopModel):
    """Neutral basal feasibility relation with explicit requested endpoint."""

    schema_id: Literal[
        "hop.basal-feasibility-landscape/v2",
        "hop.basal-feasibility-landscape/v3",
    ] = Field(default="hop.basal-feasibility-landscape/v2", alias="schema")
    projection_reference: ProjectionReference
    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:basal-neighborhood-result/[0-9a-f]{64}@1$")
    renderer_version: str
    provenance: NeighborhoodProvenance
    claim_boundary: NeighborhoodClaimBoundary
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    endpoint: ConstructionEndpoint
    status: SearchCompletionStatus
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    realization_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    truncation_reasons: tuple[str, ...]
    realizations: tuple[BasalFeasibilityRow, ...]

    @model_validator(mode="after")
    def validate_projection(self) -> BasalFeasibilityProjection:
        _validate_partition_schema(
            schema_id=self.schema_id,
            sequence_partition=self.sequence_partition,
            unpartitioned_schema="hop.basal-feasibility-landscape/v2",
            partitioned_schema="hop.basal-feasibility-landscape/v3",
        )
        _validate_feasibility_status(
            status=self.status,
            realization_count=self.realization_count,
            row_count=len(self.realizations),
            ids=tuple(row.local_realization_id for row in self.realizations),
            truncation_reasons=self.truncation_reasons,
        )
        if self.endpoint is not ConstructionEndpoint.HAIRPIN_PCR_DUPLEX or any(
            row.pairing_profile is None or not row.literal_pairs for row in self.realizations
        ):
            raise ValueError("Basal projections require the exact hairpin PCR intermediate.")
        _validate_projection_reference(
            schema_id=self.schema_id,
            reference=self.projection_reference,
            projection_id=self.projection_id,
            source_result_id=self.source_result_id,
            renderer_version=self.renderer_version,
            realization_ids=tuple(row.local_realization_id for row in self.realizations),
        )
        return self


class RelaxationShellProjection(HopModel):
    """One examined relaxation shell with exact realization membership."""

    radius: int = Field(ge=0)
    status: Literal["complete", "partial"]
    candidate_count: int = Field(ge=0)
    realization_count: int = Field(ge=0)
    realization_ids: tuple[str, ...]
    rejected_count: int = Field(ge=0)
    failure_reasons: tuple[FailureReasonCount, ...]

    @model_validator(mode="after")
    def validate_membership(self) -> RelaxationShellProjection:
        if self.realization_count != len(self.realization_ids):
            raise ValueError("Relaxation-shell count must equal exact membership.")
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("Relaxation-shell membership must not repeat a realization.")
        if self.candidate_count != self.realization_count + self.rejected_count:
            raise ValueError(
                "Relaxation-shell candidates must equal accepted plus rejected candidates."
            )
        codes = tuple(item.code for item in self.failure_reasons)
        if len(codes) != len(set(codes)):
            raise ValueError("Relaxation-shell failure reasons must be unique.")
        if sum(item.count for item in self.failure_reasons) != self.rejected_count:
            raise ValueError("Relaxation-shell failure reasons must partition rejected candidates.")
        return self


class RelaxationFrontierProjection(HopModel):
    """Exact-first relaxation frontier without inferred shell failure categories."""

    schema_id: Literal[
        "hop.foldback-relaxation-frontier/v2",
        "hop.foldback-relaxation-frontier/v3",
        "hop.basal-relaxation-frontier/v1",
        "hop.basal-relaxation-frontier/v2",
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
    status: SearchCompletionStatus
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    coordinate_names: tuple[str, ...]
    truncation_reasons: tuple[str, ...]
    shells: tuple[RelaxationShellProjection, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_projection(self) -> RelaxationFrontierProjection:
        if self.family == "foldback":
            _validate_partition_schema(
                schema_id=self.schema_id,
                sequence_partition=self.sequence_partition,
                unpartitioned_schema="hop.foldback-relaxation-frontier/v2",
                partitioned_schema="hop.foldback-relaxation-frontier/v3",
            )
        else:
            _validate_partition_schema(
                schema_id=self.schema_id,
                sequence_partition=self.sequence_partition,
                unpartitioned_schema="hop.basal-relaxation-frontier/v1",
                partitioned_schema="hop.basal-relaxation-frontier/v2",
            )
        radii = tuple(shell.radius for shell in self.shells)
        if radii != tuple(range(len(radii))):
            raise ValueError("Relaxation-frontier shells must be contiguous and exact-first.")
        partial_shells = tuple(
            index for index, shell in enumerate(self.shells) if shell.status == "partial"
        )
        if partial_shells and partial_shells != (len(self.shells) - 1,):
            raise ValueError("Only the final relaxation shell may be partial.")
        if self.status is not SearchCompletionStatus.TRUNCATED and partial_shells:
            raise ValueError("Only a truncated frontier may contain a partial shell.")
        member_ids = tuple(item for shell in self.shells for item in shell.realization_ids)
        if len(member_ids) != len(set(member_ids)):
            raise ValueError("Relaxation-frontier shells must partition exact membership.")
        if self.status is SearchCompletionStatus.TRUNCATED:
            if not self.truncation_reasons:
                raise ValueError("Truncated relaxation projections require a reason.")
        elif self.truncation_reasons:
            raise ValueError("Only truncated relaxation projections may report truncation.")
        _validate_projection_reference(
            schema_id=self.schema_id,
            reference=self.projection_reference,
            projection_id=self.projection_id,
            source_result_id=self.source_result_id,
            renderer_version=self.renderer_version,
            realization_ids=member_ids,
        )
        return self


LocalScientificProjection = Annotated[
    FoldbackFeasibilityProjection | BasalFeasibilityProjection | RelaxationFrontierProjection,
    Field(discriminator="schema_id"),
]


def _validate_partition_schema(
    *,
    schema_id: str,
    sequence_partition: SequenceDomainPartition | None,
    unpartitioned_schema: str,
    partitioned_schema: str,
) -> None:
    expected = partitioned_schema if sequence_partition is not None else unpartitioned_schema
    if schema_id != expected:
        raise ValueError("Projection schema must match its sequence-domain scope.")


def _validate_feasibility_status(
    *,
    status: SearchCompletionStatus,
    realization_count: int,
    row_count: int,
    ids: tuple[str, ...],
    truncation_reasons: tuple[str, ...],
) -> None:
    if realization_count != row_count:
        raise ValueError("Feasibility count must equal exact realization rows.")
    if len(ids) != len(set(ids)):
        raise ValueError("Feasibility rows must not repeat a local realization.")
    if status is SearchCompletionStatus.INFEASIBLE and realization_count:
        raise ValueError("Infeasible projections cannot contain realizations.")
    if status is SearchCompletionStatus.COMPLETE and not realization_count:
        raise ValueError("Complete projections require at least one realization.")
    if status is SearchCompletionStatus.TRUNCATED:
        if not truncation_reasons:
            raise ValueError("Truncated projections require a reason.")
    elif truncation_reasons:
        raise ValueError("Only truncated projections may report truncation.")


def _validate_projection_reference(
    *,
    schema_id: str,
    reference: ProjectionReference,
    projection_id: str,
    source_result_id: str,
    renderer_version: str,
    realization_ids: tuple[str, ...],
) -> None:
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
