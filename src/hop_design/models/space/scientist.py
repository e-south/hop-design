"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/space/scientist.py

Defines authored substrate spaces and complete verified digital design sets.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import normalize_dna_sequence


class PayloadSegment(HopModel):
    """One fixed or variable segment on the authored payload arm."""

    fixed: str | None = None
    variable: str | None = None
    label: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")

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


class SubstrateSpaceSpec(HopModel):
    """One minimal, single-arm substrate-space specification."""

    schema_id: Literal["hop/substrate-space/v1"] = Field(
        default="hop/substrate-space/v1", alias="schema"
    )
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    question: str | None = None
    payload: tuple[PayloadSegment, ...] = Field(min_length=1)

    @field_validator("payload", mode="before")
    @classmethod
    def normalize_payload(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def require_unique_labels(self) -> SubstrateSpaceSpec:
        labels = tuple(segment.label for segment in self.payload if segment.label is not None)
        if len(labels) != len(set(labels)):
            raise ValueError("Segment labels must be unique.")
        return self


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
    compilation_limit: int = Field(ge=1)
    message: str | None = None


class MolecularSubstrateSpace(HopModel):
    """Normalized molecular rules that define one substrate-space authority."""

    schema_id: Literal["hop.molecular-substrate-space/v1"] = Field(
        default="hop.molecular-substrate-space/v1", alias="schema"
    )
    payload_domains: tuple[tuple[Literal["A", "C", "G", "T"], ...], ...] = Field(min_length=1)
    defaults_ref: ReferenceId

    @field_validator("payload_domains")
    @classmethod
    def require_canonical_domains(
        cls,
        value: tuple[tuple[Literal["A", "C", "G", "T"], ...], ...],
    ) -> tuple[tuple[Literal["A", "C", "G", "T"], ...], ...]:
        canonical_order = ("A", "C", "G", "T")
        for domain in value:
            expected = tuple(base for base in canonical_order if base in domain)
            if not domain or domain != expected:
                raise ValueError(
                    "Payload domains must be nonempty and canonically A/C/G/T ordered."
                )
        return value


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


class CompleteSpaceAccountingClaim(HopModel):
    """Authoritative status for exhaustive substrate-space accounting."""

    status: Literal["complete"]
    basis: Literal["all_declared_assignments_enumerated"]


class VerifiedDigitalDesignClaim(HopModel):
    """Authoritative status for replay-verified digital member designs."""

    status: Literal["verified"]
    basis: Literal["all_unique_member_authorities_replay_verified"]


class NotEvaluatedClaim(HopModel):
    """Status for a downstream compatibility question not evaluated here."""

    status: Literal["not_evaluated"]


class NotRecordedClaim(HopModel):
    """Status for experimental evidence absent from the design-set authority."""

    status: Literal["not_recorded"]


class DesignSetClaimStatus(HopModel):
    """Independent claims and nonclaims established by one design set."""

    space_accounting: CompleteSpaceAccountingClaim
    digital_design: VerifiedDigitalDesignClaim
    named_method: NotEvaluatedClaim
    destination_compatibility: NotEvaluatedClaim
    physical_construction: NotRecordedClaim
    quality_control: NotRecordedClaim
    biological_activity: NotRecordedClaim


class HairpinDesignSet(HopModel):
    """Canonical manifest for one complete verified digital design set."""

    schema_id: Literal["hop.hairpin-design-set/v2"] = Field(
        default="hop.hairpin-design-set/v2", alias="schema"
    )
    design_set_id: str
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
    claim_status: DesignSetClaimStatus
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
