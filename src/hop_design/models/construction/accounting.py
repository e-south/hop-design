"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/accounting.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import normalize_dna_sequence


class SearchCompletionStatus(StrEnum):
    """Truthful disposition of one bounded scientific search."""

    COMPLETE = "complete"
    INFEASIBLE = "infeasible"
    STOPPED_BY_POLICY = "stopped_by_policy"
    TRUNCATED = "truncated"


class SearchFeasibilityStatus(StrEnum):
    """Existence claim supported by the work completed for one search."""

    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNKNOWN = "unknown"


class SearchTerminationReason(StrEnum):
    """Concrete reason one bounded search stopped."""

    EXHAUSTED_DOMAIN = "exhausted_domain"
    RESULT_QUOTA = "result_quota"
    REQUESTED_QUOTA = "requested_quota"
    EVALUATION_CAP = "evaluation_cap"
    TIME_CAP = "time_cap"
    MEMORY_GUARD = "memory_guard"
    INTERRUPTION = "interruption"


class SearchDisposition(HopModel):
    """Separate search coverage from the existence claim it can support."""

    completion: SearchCompletionStatus
    feasibility: SearchFeasibilityStatus
    termination_reason: SearchTerminationReason

    @model_validator(mode="after")
    def validate_claim_scope(self) -> SearchDisposition:
        if self.completion is SearchCompletionStatus.COMPLETE:
            if self.feasibility is SearchFeasibilityStatus.UNKNOWN:
                raise ValueError("Complete search coverage must resolve feasibility.")
            if self.termination_reason is not SearchTerminationReason.EXHAUSTED_DOMAIN:
                raise ValueError("Complete search coverage requires exhausted_domain.")
        elif self.completion is SearchCompletionStatus.STOPPED_BY_POLICY:
            if self.feasibility is SearchFeasibilityStatus.INFEASIBLE:
                raise ValueError("A policy-stopped search cannot establish infeasibility.")
            if self.termination_reason not in {
                SearchTerminationReason.RESULT_QUOTA,
                SearchTerminationReason.REQUESTED_QUOTA,
            }:
                raise ValueError("Policy-stopped search requires an explicit quota reason.")
        elif self.completion is SearchCompletionStatus.TRUNCATED:
            if self.feasibility is SearchFeasibilityStatus.INFEASIBLE:
                raise ValueError("A truncated search cannot establish infeasibility.")
            if self.termination_reason in {
                SearchTerminationReason.EXHAUSTED_DOMAIN,
                SearchTerminationReason.RESULT_QUOTA,
                SearchTerminationReason.REQUESTED_QUOTA,
            }:
                raise ValueError("Truncated search requires a resource or interruption reason.")
        else:
            raise ValueError("Infeasible is a feasibility state, not a completion state.")
        return self


class OverheadPosition(HopModel):
    """One retained non-payload nucleotide in an explicit local coordinate view."""

    coordinate_space: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    position: int = Field(ge=0)
    base: str
    material_role: Literal["source", "adapter", "derived"]

    @field_validator("base", mode="before")
    @classmethod
    def normalize_base(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("A retained-overhead base must be a DNA string.")
        base = normalize_dna_sequence(value, allow_degenerate=False)
        if len(base) != 1:
            raise ValueError("A retained-overhead position must contain one nucleotide.")
        return base


class RetainedOverheadLedger(HopModel):
    """Auditable non-payload positions retained in one local endpoint view."""

    neighborhood: Literal["foldback", "basal"]
    reference_state_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,95}$")
    positions: tuple[OverheadPosition, ...]
    retained_overhead_nt: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_positions(self) -> RetainedOverheadLedger:
        keys = tuple((item.coordinate_space, item.position) for item in self.positions)
        if len(keys) != len(set(keys)):
            raise ValueError("Retained-overhead positions must be unique in their coordinate view.")
        if self.retained_overhead_nt != len(self.positions):
            raise ValueError("Retained-overhead count must equal the explicit position count.")
        return self


class FailureReasonCount(HopModel):
    """Stable aggregate count for one rejected-candidate or payload-conflict reason."""

    code: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,95}$")
    count: int = Field(ge=1)


class RelaxationShellSummary(HopModel):
    """Candidate accounting and exact realization membership for one examined shell."""

    radius: int = Field(ge=0)
    examined: bool
    complete: bool
    candidate_count: int = Field(ge=0)
    realization_ids: tuple[str, ...]
    rejected_count: int = Field(ge=0)
    failure_reasons: tuple[FailureReasonCount, ...]

    @model_validator(mode="after")
    def validate_accounting(self) -> RelaxationShellSummary:
        if not self.examined and (
            self.complete
            or self.candidate_count
            or self.realization_ids
            or self.rejected_count
            or self.failure_reasons
        ):
            raise ValueError("Unexamined shells must not report candidate facts.")
        if self.examined and not self.complete and self.candidate_count == 0:
            raise ValueError("Partial examined shells must report at least one candidate.")
        if self.candidate_count != len(self.realization_ids) + self.rejected_count:
            raise ValueError(
                "Shell candidate count must equal accepted realizations plus rejected candidates."
            )
        codes = tuple(item.code for item in self.failure_reasons)
        if len(codes) != len(set(codes)):
            raise ValueError("Shell failure-reason codes must be unique.")
        if codes != tuple(sorted(codes)):
            raise ValueError("Shell failure reasons must use canonical code order.")
        if sum(item.count for item in self.failure_reasons) != self.rejected_count:
            raise ValueError("Shell failure-reason counts must partition rejected candidates.")
        return self


class PayloadCompatibilityStatus(StrEnum):
    """Whether bounded payload compatibility was exhaustively calculated."""

    COMPLETE = "complete"
    NOT_COMPUTED = "not_computed"


class PayloadCompatibilityAccounting(HopModel):
    """Exact or explicitly unavailable route compatibility across payload assignments."""

    status: PayloadCompatibilityStatus
    total_assignments: int = Field(ge=1)
    compatible_assignments: int | None = Field(default=None, ge=0)
    excluded_assignments: int | None = Field(default=None, ge=0)
    conflict_counts: tuple[FailureReasonCount, ...] = ()
    exhaustive: bool
    warning: str | None = None

    @model_validator(mode="after")
    def validate_accounting(self) -> PayloadCompatibilityAccounting:
        codes = tuple(item.code for item in self.conflict_counts)
        if len(codes) != len(set(codes)):
            raise ValueError("Payload-conflict reason codes must be unique.")
        if codes != tuple(sorted(codes)):
            raise ValueError("Payload-conflict reasons must use canonical code order.")
        if self.status is PayloadCompatibilityStatus.COMPLETE:
            if not self.exhaustive:
                raise ValueError("Complete payload accounting must be exhaustive.")
            if self.compatible_assignments is None or self.excluded_assignments is None:
                raise ValueError("Complete payload accounting requires exact assignment counts.")
            if self.compatible_assignments + self.excluded_assignments != self.total_assignments:
                raise ValueError("Payload compatibility counts must equal total assignments.")
            if any(item.count > self.excluded_assignments for item in self.conflict_counts):
                raise ValueError("A payload-conflict count cannot exceed excluded assignments.")
        else:
            if self.exhaustive:
                raise ValueError("Uncomputed payload accounting cannot be exhaustive.")
            if self.compatible_assignments is not None or self.excluded_assignments is not None:
                raise ValueError("Uncomputed payload accounting must not report exact counts.")
            if self.conflict_counts:
                raise ValueError("Uncomputed payload accounting must not report exact conflicts.")
            if not self.warning:
                raise ValueError("Uncomputed payload accounting requires a conservative warning.")
        return self


class NeighborhoodProvenance(HopModel):
    """Replay-relevant implementation and catalog facts for one neighborhood result."""

    hop_version: str
    route_implementation_version: str
    enzyme_catalog_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class ProjectionInventoryStatus(StrEnum):
    """Availability of one non-authoritative result projection."""

    AVAILABLE = "available"
    NOT_GENERATED = "not_generated"


class ProjectionInventoryItem(HopModel):
    """Declared renderer projection without output-path authority."""

    projection_schema: str
    renderer_version: str
    status: ProjectionInventoryStatus
    projection_id: str | None = None

    @model_validator(mode="after")
    def validate_availability(self) -> ProjectionInventoryItem:
        if (self.status is ProjectionInventoryStatus.AVAILABLE) != bool(self.projection_id):
            raise ValueError(
                "Available projections require an id; absent projections must omit it."
            )
        return self


class DigitalDesignStatus(StrEnum):
    """Digital authority status exposed by a construction result."""

    VERIFIED = "verified"


class MethodResolutionStatus(StrEnum):
    """Whether a complete material-bound method realization was resolved."""

    RESOLVED = "resolved_under_declared_molecular_model"
    NOT_RESOLVED = "not_resolved"


class ExperimentalEvidenceStatus(StrEnum):
    """Status for experimental evidence outside digital construction discovery."""

    NOT_RECORDED = "not_recorded"


class NeighborhoodClaimBoundary(HopModel):
    """Dimension-specific claims established or explicitly absent from a local result."""

    digital_design: DigitalDesignStatus
    method: MethodResolutionStatus
    physical_construction: ExperimentalEvidenceStatus = ExperimentalEvidenceStatus.NOT_RECORDED
    quality_control: ExperimentalEvidenceStatus = ExperimentalEvidenceStatus.NOT_RECORDED
    biological_activity: ExperimentalEvidenceStatus = ExperimentalEvidenceStatus.NOT_RECORDED


class RealizationGrouping(StrEnum):
    """Supported non-authoritative grouping dimensions."""

    ACHIEVED_GEOMETRY = "achieved_geometry"
    FINAL_PRODUCT = "final_product"


class RealizationGroup(HopModel):
    """One reversible presentation group over exact realization identities."""

    grouping: RealizationGrouping
    group_key: str
    realization_ids: tuple[str, ...] = Field(min_length=1)
    multiplicity: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_multiplicity(self) -> RealizationGroup:
        if self.multiplicity != len(self.realization_ids):
            raise ValueError("Group multiplicity must equal its exact member count.")
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("A realization group must not repeat a member.")
        expected_prefix = {
            RealizationGrouping.ACHIEVED_GEOMETRY: "hop:geometry/",
            RealizationGrouping.FINAL_PRODUCT: "hop:final-product/",
        }[self.grouping]
        if not self.group_key.startswith(expected_prefix):
            raise ValueError("Group key must match the declared grouping dimension.")
        return self
