"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/design_space.py

Defines authored substrate spaces, exact design sets, and advanced Cartesian plans.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.basal_policy import BasalDesignRequest
from hop_design.models.base import HopModel
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.diagnostics import CheckReport
from hop_design.models.foldback import FoldbackEvaluationRequest
from hop_design.models.references import ExternalRef, ReferenceId
from hop_design.models.sequence import normalize_dna_sequence
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

    schema_id: Literal["hop.resolved-design-space/v2"] = Field(
        default="hop.resolved-design-space/v2",
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
    design_derivation_ref: ReferenceId
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

    schema_id: Literal["hop.design-space-plan/v2"] = Field(
        default="hop.design-space-plan/v2",
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


class SubstrateSpaceContext(HopModel):
    """Descriptive experimental context excluded from design-set identity."""

    question: str | None = None
    activity: str | None = None
    readout: str | None = None


class PayloadSegment(HopModel):
    """One fixed or variable segment on the authored payload arm."""

    fixed: str | None = None
    variable: str | None = None
    name: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")

    @field_validator("fixed", mode="before")
    @classmethod
    def normalize_fixed(cls, value: object) -> str | None:
        if value is None:
            return None
        return normalize_dna_sequence(value, allow_degenerate=False)  # type: ignore[arg-type]

    @field_validator("variable", mode="before")
    @classmethod
    def normalize_variable(cls, value: object) -> str | None:
        if value is None:
            return None
        return normalize_dna_sequence(value, allow_degenerate=True)  # type: ignore[arg-type]

    @model_validator(mode="after")
    def require_one_segment_kind(self) -> PayloadSegment:
        if (self.fixed is None) == (self.variable is None):
            raise ValueError("Each payload segment must define exactly one of fixed or variable.")
        return self


class SegmentedPayload(HopModel):
    """The single authored payload arm as ordered named segments."""

    segments: tuple[PayloadSegment, ...] = Field(min_length=1)

    @field_validator("segments", mode="before")
    @classmethod
    def normalize_segments(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def require_unique_names(self) -> SegmentedPayload:
        names = tuple(segment.name for segment in self.segments if segment.name is not None)
        if len(names) != len(set(names)):
            raise ValueError("Segment names must be unique.")
        return self


class HairpinDefaults(HopModel):
    """Registered hairpin anatomy used for every member."""

    defaults_ref: ReferenceId


class ExhaustiveEnumeration(HopModel):
    """Explicit exhaustive enumeration and allocation bound."""

    mode: Literal["exhaustive"] = "exhaustive"
    max_members: int = Field(ge=1, le=100_000)


class SubstrateSpaceSpec(HopModel):
    """One bounded, single-arm substrate-space specification."""

    schema_id: Literal["hop/substrate-space/v1"] = Field(
        default="hop/substrate-space/v1", alias="schema"
    )
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    context: SubstrateSpaceContext | None = None
    payload: SegmentedPayload
    hairpin: HairpinDefaults
    enumeration: ExhaustiveEnumeration


class SubstrateSpacePreview(HopModel):
    """Allocation-free accounting for one authored substrate space."""

    state: Literal["ready", "blocked", "invalid"]
    name: str
    authored_payload: str
    derived_paired_payload: str
    fixed_positions: tuple[int, ...]
    variable_positions: tuple[int, ...]
    variable_domains: tuple[tuple[str, ...], ...]
    paired_positions: tuple[tuple[int, int], ...]
    theoretical_cardinality: int = Field(ge=1)
    max_members: int = Field(ge=1)
    message: str | None = None


class VariableAssignment(HopModel):
    """One exact base assigned to one authored variable position."""

    position: int = Field(ge=1)
    base: Literal["A", "C", "G", "T"]


class HairpinDesignMember(HopModel):
    """One manifest record in a complete hairpin design set."""

    canonical_ordinal: int = Field(ge=1)
    variable_assignment: tuple[VariableAssignment, ...]
    exact_payload: str
    derived_paired_payload: str
    exact_hairpin_length: int = Field(ge=1)
    exact_encoding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    member_bundle_id: str
    member_bundle_path: str
    disposition: Literal["canonical", "duplicate"]
    canonical_member_ordinal: int | None = Field(default=None, ge=1)

    @field_validator("member_bundle_path")
    @classmethod
    def require_confined_member_bundle_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or "\\" in value
            or value != path.as_posix()
            or len(path.parts) != 2
            or path.parts[0] != "members"
            or path.parts[1] in {"", ".", ".."}
        ):
            raise ValueError("Member bundle path must be members/<member-id>.")
        return value

    @model_validator(mode="after")
    def validate_disposition_reference(self) -> HairpinDesignMember:
        if (self.disposition == "canonical") != (self.canonical_member_ordinal is None):
            raise ValueError("Member disposition and canonical reference disagree.")
        return self


class HairpinDesignSet(HopModel):
    """Canonical manifest for one complete verified digital design set."""

    schema_id: Literal["hop.hairpin-design-set/v1"] = Field(
        default="hop.hairpin-design-set/v1", alias="schema"
    )
    design_set_id: str
    name: str
    spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    defaults_ref: ReferenceId
    theoretical_cardinality: int = Field(ge=1)
    enumerated_assignments: int = Field(ge=1)
    unique_designs: int = Field(ge=1)
    duplicate_count: int = Field(ge=0)
    coverage: Literal["complete"] = "complete"
    ordering_contract: Literal["variable-positions-5prime-acgt-v1"] = (
        "variable-positions-5prime-acgt-v1"
    )
    members: tuple[HairpinDesignMember, ...]
    artifacts: tuple[ArtifactManifestEntry, ...]
    manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_complete_accounting(self) -> HairpinDesignSet:
        if self.enumerated_assignments != self.theoretical_cardinality:
            raise ValueError("Complete coverage requires every theoretical assignment.")
        if len(self.members) != self.enumerated_assignments:
            raise ValueError("Member records must account for every enumerated assignment.")
        if self.unique_designs + self.duplicate_count != self.enumerated_assignments:
            raise ValueError("Unique and duplicate counts must account for every assignment.")
        ordinals = tuple(member.canonical_ordinal for member in self.members)
        if ordinals != tuple(range(1, self.enumerated_assignments + 1)):
            raise ValueError("Member ordinals must be complete and canonically ordered.")
        artifact_paths = tuple(artifact.path for artifact in self.artifacts)
        if len(artifact_paths) != len(set(artifact_paths)):
            raise ValueError("Design-set artifact paths must be unique.")
        return self


__all__ = [
    "BasalOption",
    "DesignSpaceLimits",
    "DesignSpacePlan",
    "DesignSpaceRow",
    "DuplicateDesignSequencePolicy",
    "FoldbackOption",
    "HairpinDesignMember",
    "HairpinDesignSet",
    "ReleaseOption",
    "ResolvedDesignSpace",
    "SubstrateSpacePreview",
    "SubstrateSpaceSpec",
    "VariableAssignment",
]
