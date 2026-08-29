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

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class SearchCompletionStatus(StrEnum):
    """Truthful disposition of one bounded scientific search."""

    COMPLETE = "complete"
    INFEASIBLE = "infeasible"
    TRUNCATED = "truncated"


class RelaxationShellSummary(HopModel):
    """Completion evidence and exact realization membership for one examined shell."""

    radius: int = Field(ge=0)
    examined: bool
    realization_ids: tuple[str, ...]


class FailureReasonCount(HopModel):
    """Stable aggregate count for one rejected-candidate or payload-conflict reason."""

    code: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,95}$")
    count: int = Field(ge=1)


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
