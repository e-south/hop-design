"""Strict Cartesian design-space and review-plan contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.basal import BasalDesignRequest
from hop_design.models.base import HopModel
from hop_design.models.diagnostics import CheckReport
from hop_design.models.foldback import FoldbackEvaluationRequest
from hop_design.models.references import ExternalRef, ReferenceId
from hop_design.models.sources import PayloadCollection
from hop_design.models.spec import DesignLimits, ResolvedHopSpec
from hop_design.models.strand_state import ReleaseProjectionRequest


class FoldbackOption(HopModel):
    """One caller-identified foldback request on a design-space axis."""

    option_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    request: FoldbackEvaluationRequest


class BasalOption(HopModel):
    """One caller-identified basal request on a design-space axis."""

    option_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    request: BasalDesignRequest


class ReleaseOption(HopModel):
    """One explicit release request or an explicit no-release axis value."""

    option_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    request: ReleaseProjectionRequest | None


class DesignSpaceLimits(HopModel):
    """Hard pre-allocation bound for one Cartesian design space."""

    max_designs: int = Field(ge=1, le=1_000_000)


class DuplicateDesignSequencePolicy(StrEnum):
    """Explicit disposition when multiple combinations yield one final sequence."""

    FAIL = "fail"
    KEEP = "keep"


class ResolvedDesignSpace(HopModel):
    """Composable payload, foldback, basal, and release axes with shared locks."""

    schema_id: Literal["hop.resolved-design-space/v1"] = Field(
        default="hop.resolved-design-space/v1",
        alias="schema",
    )
    space_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,47}$")
    payloads: PayloadCollection
    foldbacks: tuple[FoldbackOption, ...] = Field(min_length=1)
    basals: tuple[BasalOption, ...] = Field(min_length=1)
    releases: tuple[ReleaseOption, ...] = Field(min_length=1)
    defaults_ref: ReferenceId
    catalog_ref: ReferenceId
    constraint_profile_ref: ReferenceId
    processing_route_ref: ReferenceId
    per_design_constraints: DesignLimits
    limits: DesignSpaceLimits
    duplicate_final_sequence_policy: DuplicateDesignSequencePolicy
    external_refs: tuple[ExternalRef, ...] = ()

    @model_validator(mode="after")
    def validate_axis_ids(self) -> ResolvedDesignSpace:
        for label, options in (
            ("Foldback", self.foldbacks),
            ("Basal", self.basals),
            ("Release", self.releases),
        ):
            option_ids = tuple(option.option_id for option in options)
            if len(option_ids) != len(set(option_ids)):
                raise ValueError(f"{label} option ids must be unique within their axis.")
        return self


class DesignSpaceRow(HopModel):
    """One deterministic Cartesian combination and its check report."""

    payload_record_id: str
    foldback_option_id: str
    basal_option_id: str
    release_option_id: str
    spec: ResolvedHopSpec
    report: CheckReport
    projected_final_sequence: str | None


class DesignSpacePlan(HopModel):
    """A renderer-free review table for every bounded combination."""

    schema_id: Literal["hop.design-space-plan/v1"] = Field(
        default="hop.design-space-plan/v1",
        alias="schema",
    )
    space_id: str
    cardinality: int = Field(ge=1)
    feasible_count: int = Field(ge=0)
    infeasible_count: int = Field(ge=0)
    duplicate_final_sequence_count: int = Field(ge=0)
    rows: tuple[DesignSpaceRow, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> DesignSpacePlan:
        if len(self.rows) != self.cardinality:
            raise ValueError("Design-space row count must equal Cartesian cardinality.")
        feasible = sum(not row.report.has_errors for row in self.rows)
        if self.feasible_count != feasible:
            raise ValueError("feasible_count must match row reports.")
        if self.infeasible_count != self.cardinality - feasible:
            raise ValueError("infeasible_count must match row reports.")
        seen_sequences: set[str] = set()
        duplicate_count = 0
        for row in self.rows:
            sequence = row.projected_final_sequence
            if sequence is None:
                if not row.report.has_errors:
                    raise ValueError("Feasible design-space rows require a projected sequence.")
                continue
            if row.report.has_errors:
                raise ValueError("Infeasible design-space rows cannot project a final sequence.")
            if sequence in seen_sequences:
                duplicate_count += 1
            seen_sequences.add(sequence)
        if self.duplicate_final_sequence_count != duplicate_count:
            raise ValueError("duplicate_final_sequence_count must match projected sequences.")
        design_ids = tuple(row.spec.design_id for row in self.rows)
        if len(design_ids) != len(set(design_ids)):
            raise ValueError("Design-space rows must have unique derived design ids.")
        return self


__all__ = [
    "BasalOption",
    "DesignSpaceLimits",
    "DesignSpacePlan",
    "DesignSpaceRow",
    "DuplicateDesignSequencePolicy",
    "FoldbackOption",
    "ReleaseOption",
    "ResolvedDesignSpace",
]
