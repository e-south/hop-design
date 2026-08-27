"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/spaces.py

Defines authored substrate spaces, symbolic previews, and design-set manifests.

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
        if self.disposition == "canonical" and self.canonical_member_ordinal is not None:
            raise ValueError("A canonical member must not reference another member.")
        if self.disposition == "duplicate" and self.canonical_member_ordinal is None:
            raise ValueError("A duplicate member must reference its canonical member ordinal.")
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
    "HairpinDesignMember",
    "HairpinDesignSet",
    "SubstrateSpacePreview",
    "SubstrateSpaceSpec",
    "VariableAssignment",
]
