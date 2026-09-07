"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/basal.py

Defines lossless scientific projections of basal-neighborhood discovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    NeighborhoodClaimBoundary,
    NeighborhoodProvenance,
    SearchDisposition,
)
from hop_design.models.construction.basal.pairing import BasalPairRecord
from hop_design.models.construction.basal_release import BasalFutureReleaseAction
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.projection import ProjectionReference
from hop_design.models.construction.sequence_domain import SequenceDomainPartition
from hop_design.models.construction.targets import BasalPairClass
from hop_design.models.junction import Strand

from .validation import (
    validate_feasibility_disposition,
    validate_partition_schema,
    validate_projection_reference,
)

BASAL_PROJECTION_RENDERER_VERSION = "basal-projections/4"
BASAL_PART_PROJECTION_RENDERER_VERSION = "basal-projections/5"
BASAL_MATRIX_RENDERER_VERSION = "basal-minimum-overhead-matrix/1"
BASAL_PART_MATRIX_RENDERER_VERSION = "basal-minimum-overhead-matrix/2"


class BasalFeasibilityRow(HopModel):
    """One exact local basal realization and its upstream obligations."""

    local_realization_id: str = Field(pattern=r"^hop:local-realization/[0-9a-f]{64}@1$")
    basal_realization_id: str = Field(pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$")
    retained_overhead_nt: int = Field(ge=0)
    nick_enzyme_id: str
    future_release_action_id: str | None = None
    future_release_enzyme_id: str | None = None
    nick_strand: Strand
    nick_offset_nt: int = Field(ge=0)
    pairing_pattern: str | None
    pairing_classes: tuple[BasalPairClass, ...]
    literal_pairs: tuple[BasalPairRecord, ...]
    proximal_annealing_nt: int = Field(ge=1)
    required_annealing_nt: int = Field(ge=1)
    annealing_completion_nt: int = Field(ge=0)
    mismatch_fraction: float = Field(ge=0.0, le=1.0)
    warnings: tuple[Literal["mismatch-fraction-above-threshold"], ...] = ()

    @model_validator(mode="after")
    def validate_exact_details(self) -> BasalFeasibilityRow:
        if self.pairing_classes != tuple(item.pair_class for item in self.literal_pairs):
            raise ValueError("Basal pairing classes must replay every literal pair.")
        if (self.future_release_action_id is None) != (self.future_release_enzyme_id is None):
            raise ValueError("A future release action and enzyme must be present together.")
        return self


class BasalFeasibilityProjection(HopModel):
    """Neutral basal feasibility relation with explicit requested endpoint."""

    schema_id: Literal[
        "hop.basal-feasibility-landscape/v4",
        "hop.basal-feasibility-landscape/v5",
    ] = Field(default="hop.basal-feasibility-landscape/v4", alias="schema")
    projection_reference: ProjectionReference
    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:basal-neighborhood-result/[0-9a-f]{64}@1$")
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
    realizations: tuple[BasalFeasibilityRow, ...]

    @model_validator(mode="after")
    def validate_projection(self) -> BasalFeasibilityProjection:
        validate_partition_schema(
            schema_id=self.schema_id,
            sequence_partition=self.sequence_partition,
            unpartitioned_schema="hop.basal-feasibility-landscape/v4",
            partitioned_schema="hop.basal-feasibility-landscape/v5",
        )
        validate_feasibility_disposition(
            disposition=self.disposition,
            realization_count=self.realization_count,
            row_count=len(self.realizations),
            ids=tuple(row.local_realization_id for row in self.realizations),
        )
        if self.endpoint not in {
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            ConstructionEndpoint.CLONE_READY_DUPLEX,
        } or any(row.pairing_pattern is None or not row.literal_pairs for row in self.realizations):
            raise ValueError("Basal projections require a PCR-bearing local boundary.")
        has_release = self.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX
        if any(
            (row.future_release_action_id is not None) is not has_release
            for row in self.realizations
        ):
            raise ValueError("Basal future release obligations must follow the requested endpoint.")
        validate_projection_reference(
            schema_id=self.schema_id,
            reference=self.projection_reference,
            projection_id=self.projection_id,
            source_result_id=self.source_result_id,
            renderer_version=self.renderer_version,
            realization_ids=tuple(row.local_realization_id for row in self.realizations),
        )
        return self


class BasalMinimumOverheadCell(HopModel):
    """One basal nickase and future-release action disposition."""

    nick_enzyme_id: str
    future_release_action_id: str = Field(
        pattern=r"^hop:basal-future-release-action/[0-9a-f]{64}@1$"
    )
    status: Literal["proven_minimum", "infeasible", "unknown"]
    minimum_retained_overhead_nt: int | None = Field(default=None, ge=0)
    realization_count: int = Field(ge=0)
    realization_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_disposition(self) -> BasalMinimumOverheadCell:
        if self.realization_count != len(self.realization_ids):
            raise ValueError("Matrix cell count must equal exact realization membership.")
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("Matrix cell membership must not repeat a realization.")
        if self.status == "proven_minimum":
            if self.minimum_retained_overhead_nt is None or not self.realization_ids:
                raise ValueError("A proven matrix minimum requires exact realization evidence.")
        elif self.minimum_retained_overhead_nt is not None or self.realization_ids:
            raise ValueError("A matrix cell without a solution cannot carry realization evidence.")
        return self


class BasalMinimumOverheadMatrixProjection(HopModel):
    """Local nickase by future-release action minimum-overhead relation."""

    schema_id: Literal[
        "hop.basal-minimum-overhead-matrix/v1",
        "hop.basal-minimum-overhead-matrix/v2",
    ] = Field(default="hop.basal-minimum-overhead-matrix/v1", alias="schema")
    projection_reference: ProjectionReference
    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:basal-neighborhood-result/[0-9a-f]{64}@1$")
    renderer_version: str
    provenance: NeighborhoodProvenance
    claim_boundary: NeighborhoodClaimBoundary
    problem_id: str = Field(pattern=r"^hop:construction-problem/[0-9a-f]{64}@1$")
    endpoint: Literal[ConstructionEndpoint.CLONE_READY_DUPLEX]
    disposition: SearchDisposition
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    max_retained_overhead_nt: int = Field(ge=0)
    nick_enzyme_ids: tuple[str, ...] = Field(min_length=1)
    release_actions: tuple[BasalFutureReleaseAction, ...] = Field(min_length=1)
    realization_ids: tuple[str, ...]
    cells: tuple[BasalMinimumOverheadCell, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_matrix(self) -> BasalMinimumOverheadMatrixProjection:
        validate_partition_schema(
            schema_id=self.schema_id,
            sequence_partition=self.sequence_partition,
            unpartitioned_schema="hop.basal-minimum-overhead-matrix/v1",
            partitioned_schema="hop.basal-minimum-overhead-matrix/v2",
        )
        if self.nick_enzyme_ids != tuple(sorted(set(self.nick_enzyme_ids))):
            raise ValueError("Matrix nickase axes must use unique canonical order.")
        action_ids = tuple(action.action_id for action in self.release_actions)
        if action_ids != tuple(sorted(set(action_ids))):
            raise ValueError("Matrix release-action axes must use unique canonical order.")
        expected_keys = tuple(
            (nick_enzyme_id, action_id)
            for nick_enzyme_id in self.nick_enzyme_ids
            for action_id in action_ids
        )
        observed_keys = tuple(
            (cell.nick_enzyme_id, cell.future_release_action_id) for cell in self.cells
        )
        if observed_keys != expected_keys:
            raise ValueError("Matrix cells must cover the canonical axis product exactly once.")
        cell_ids = tuple(
            realization_id for cell in self.cells for realization_id in cell.realization_ids
        )
        if Counter(cell_ids) != Counter(self.realization_ids) or len(cell_ids) != len(
            set(cell_ids)
        ):
            raise ValueError("Matrix cells must partition every exact realization once.")
        if any(
            cell.minimum_retained_overhead_nt is not None
            and cell.minimum_retained_overhead_nt > self.max_retained_overhead_nt
            for cell in self.cells
        ):
            raise ValueError("Matrix minima must remain inside the declared overhead envelope.")
        complete = self.disposition.completion == "complete"
        if any(cell.status == "infeasible" for cell in self.cells) and not complete:
            raise ValueError("Only complete search coverage can establish an infeasible cell.")
        if any(cell.status == "unknown" for cell in self.cells) and complete:
            raise ValueError("Complete search coverage cannot leave an unknown matrix cell.")
        validate_projection_reference(
            schema_id=self.schema_id,
            reference=self.projection_reference,
            projection_id=self.projection_id,
            source_result_id=self.source_result_id,
            renderer_version=self.renderer_version,
            realization_ids=self.realization_ids,
        )
        return self
