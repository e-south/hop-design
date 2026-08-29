"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/enzymes.py

Defines vendor-neutral characterized enzymes and caller provisioning policy.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.references import ExternalRef, ReferenceId
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence
from hop_design.serialization import canonical_json_bytes, sha256_digest


class EnzymeClass(StrEnum):
    """The physical cleavage class represented by a characterized entry."""

    NICKASE = "nickase"
    DUPLEX_RESTRICTION = "duplex_restriction"


class TargetMolecule(StrEnum):
    """The molecule class recognized by an enzyme."""

    DNA = "dna"


class RecognitionOrientationSemantics(StrEnum):
    """Which motif orientations are physically recognized."""

    DECLARED_ONLY = "declared_only"
    BOTH_ORIENTATIONS = "both_orientations"


class SubstrateRequirement(StrEnum):
    """The strand state required for an enzyme site to be actionable."""

    DUPLEX_DNA = "duplex_dna"
    SINGLE_OR_DUPLEX_DNA = "single_or_duplex_dna"


class ResultingEndModel(StrEnum):
    """The cleavage product class derived from the characterized cut offsets."""

    NICK = "nick"
    DUPLEX_BREAK = "duplex_break"


class EnzymeRole(StrEnum):
    """A route-local reason for applying an enzyme."""

    TERMINUS_DEFINITION = "terminus_definition"
    STRAND_EXPOSURE = "strand_exposure"
    BASAL_NICK = "basal_nick"
    FOLDBACK_NICK = "foldback_nick"
    END_GENERATION = "end_generation"


class VendorMetadata(HopModel):
    """Optional procurement metadata excluded from molecular identity."""

    vendor_name: str = Field(min_length=1)
    catalog_number: str | None = Field(default=None, min_length=1)
    buffer_notes: str | None = Field(default=None, min_length=1)
    availability: str | None = Field(default=None, min_length=1)


class CharacterizedEnzyme(HopModel):
    """One vendor-neutral recognition and cleavage definition."""

    schema_id: Literal["hop/characterized-enzyme/v1"] = Field(
        default="hop/characterized-enzyme/v1", alias="schema"
    )
    enzyme_id: ReferenceId
    canonical_name: str = Field(min_length=1)
    enzyme_class: EnzymeClass
    target_molecule: TargetMolecule
    recognition_pattern: str
    recognition_orientation_semantics: RecognitionOrientationSemantics
    recognition_length: int = Field(ge=1)
    substrate_requirement: SubstrateRequirement
    cut_offset_reference_strand: int
    cut_offset_complement_strand: int | None
    resulting_end_model: ResultingEndModel
    characterization_source: ExternalRef
    vendor_metadata: tuple[VendorMetadata, ...] = ()

    @field_validator("recognition_pattern", mode="before")
    @classmethod
    def normalize_recognition_pattern(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @field_validator("canonical_name", mode="after")
    @classmethod
    def validate_canonical_name(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("canonical_name must not contain surrounding whitespace.")
        return value

    @model_validator(mode="after")
    def validate_characterization(self) -> CharacterizedEnzyme:
        if self.recognition_length != len(self.recognition_pattern):
            raise ValueError("recognition_length must equal the recognition-pattern length.")
        if self.enzyme_class is EnzymeClass.NICKASE:
            if self.cut_offset_complement_strand is not None:
                raise ValueError("A nickase must define exactly one strand cut.")
            if self.resulting_end_model is not ResultingEndModel.NICK:
                raise ValueError("A nickase must use the nick resulting-end model.")
        elif self.cut_offset_complement_strand is None:
            raise ValueError("A duplex restriction enzyme must define both strand cuts.")
        elif self.resulting_end_model is not ResultingEndModel.DUPLEX_BREAK:
            raise ValueError("A duplex restriction enzyme must use the duplex-break end model.")
        if len(set(self.vendor_metadata)) != len(self.vendor_metadata):
            raise ValueError("vendor_metadata must not contain duplicate entries.")
        return self


def _enzyme_identity_seed(enzyme: CharacterizedEnzyme) -> dict[str, object]:
    return enzyme.model_dump(
        mode="json",
        by_alias=True,
        exclude={"vendor_metadata"},
    )


def characterized_enzyme_digest(enzyme: CharacterizedEnzyme) -> str:
    """Return molecular identity independent of procurement metadata."""
    return sha256_digest(canonical_json_bytes(_enzyme_identity_seed(enzyme)))


class CharacterizedEnzymeCatalog(HopModel):
    """A finite caller-supplied snapshot of characterized enzymes."""

    schema_id: Literal["hop/characterized-enzyme-catalog/v1"] = Field(
        default="hop/characterized-enzyme-catalog/v1", alias="schema"
    )
    catalog_id: ReferenceId
    enzymes: tuple[CharacterizedEnzyme, ...]

    @model_validator(mode="after")
    def validate_entries(self) -> CharacterizedEnzymeCatalog:
        if not self.enzymes:
            raise ValueError("A characterized enzyme catalog must not be empty.")
        enzyme_ids = tuple(enzyme.enzyme_id for enzyme in self.enzymes)
        if len(enzyme_ids) != len(set(enzyme_ids)):
            raise ValueError("Characterized enzyme ids must be unique.")
        return self

    def by_id(self, enzyme_id: str) -> CharacterizedEnzyme:
        """Resolve one characterized enzyme by its canonical id."""
        for enzyme in self.enzymes:
            if enzyme.enzyme_id == enzyme_id:
                return enzyme
        raise KeyError(enzyme_id)


def characterized_enzyme_catalog_digest(catalog: CharacterizedEnzymeCatalog) -> str:
    """Return catalog identity independent of entry order and procurement metadata."""
    seed = {
        "schema": catalog.schema_id,
        "catalog_id": catalog.catalog_id,
        "enzymes": tuple(
            _enzyme_identity_seed(enzyme)
            for enzyme in sorted(catalog.enzymes, key=lambda item: item.enzyme_id)
        ),
    }
    return sha256_digest(canonical_json_bytes(seed))


class EnzymeRoleRestriction(HopModel):
    """Limit one route role to an explicit subset of provisioned enzymes."""

    role: EnzymeRole
    allowed_enzyme_ids: tuple[ReferenceId, ...] = Field(min_length=1)

    @field_validator("allowed_enzyme_ids", mode="after")
    @classmethod
    def validate_unique_ids(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("Role-restricted enzyme ids must be unique.")
        return values


class EnzymeProvisioningPolicy(HopModel):
    """Caller-owned enzyme availability and route-role constraints."""

    catalog: CharacterizedEnzymeCatalog
    allowed_enzyme_ids: tuple[ReferenceId, ...]
    forbidden_enzyme_ids: tuple[ReferenceId, ...]
    reserved_enzyme_ids: tuple[ReferenceId, ...]
    max_operations: int | None = Field(default=None, ge=1)
    role_restrictions: tuple[EnzymeRoleRestriction, ...]

    @model_validator(mode="after")
    def validate_policy(self) -> EnzymeProvisioningPolicy:
        named_sets = {
            "allowed": self.allowed_enzyme_ids,
            "forbidden": self.forbidden_enzyme_ids,
            "reserved": self.reserved_enzyme_ids,
        }
        for name, values in named_sets.items():
            if len(values) != len(set(values)):
                raise ValueError(f"{name}_enzyme_ids must not contain duplicates.")
        catalog_ids = {enzyme.enzyme_id for enzyme in self.catalog.enzymes}
        referenced_ids = set().union(*(set(values) for values in named_sets.values()))
        unknown = referenced_ids - catalog_ids
        if unknown:
            raise ValueError(f"Provisioning policy references unknown enzymes: {sorted(unknown)}")
        names = tuple(named_sets)
        for index, left_name in enumerate(names):
            for right_name in names[index + 1 :]:
                overlap = set(named_sets[left_name]) & set(named_sets[right_name])
                if overlap:
                    raise ValueError(
                        f"{left_name} and {right_name} enzyme sets must not overlap: "
                        f"{sorted(overlap)}"
                    )
        roles = tuple(restriction.role for restriction in self.role_restrictions)
        if len(roles) != len(set(roles)):
            raise ValueError("Each enzyme role may have at most one restriction.")
        globally_allowed = set(self.allowed_enzyme_ids) if self.allowed_enzyme_ids else catalog_ids
        forbidden = set(self.forbidden_enzyme_ids)
        reserved = set(self.reserved_enzyme_ids)
        for restriction in self.role_restrictions:
            restricted_ids = set(restriction.allowed_enzyme_ids)
            unknown_restricted = restricted_ids - catalog_ids
            if unknown_restricted:
                raise ValueError(
                    f"Role restriction references unknown enzymes: {sorted(unknown_restricted)}"
                )
            if restricted_ids & reserved:
                raise ValueError("A role restriction must not authorize reserved enzymes.")
            if restricted_ids & forbidden:
                raise ValueError("A role restriction must not authorize forbidden enzymes.")
            if not restricted_ids <= globally_allowed:
                raise ValueError("A role restriction must stay within the globally allowed set.")
        return self

    def permits(self, enzyme_id: str, *, role: EnzymeRole) -> bool:
        """Return whether the caller provisioned one enzyme for one route role."""
        catalog_ids = {enzyme.enzyme_id for enzyme in self.catalog.enzymes}
        if enzyme_id not in catalog_ids:
            return False
        if self.allowed_enzyme_ids and enzyme_id not in self.allowed_enzyme_ids:
            return False
        if enzyme_id in self.forbidden_enzyme_ids or enzyme_id in self.reserved_enzyme_ids:
            return False
        for restriction in self.role_restrictions:
            if restriction.role is role:
                return enzyme_id in restriction.allowed_enzyme_ids
        return True


__all__ = [
    "CharacterizedEnzyme",
    "CharacterizedEnzymeCatalog",
    "EnzymeClass",
    "EnzymeProvisioningPolicy",
    "EnzymeRole",
    "EnzymeRoleRestriction",
    "RecognitionOrientationSemantics",
    "ResultingEndModel",
    "SubstrateRequirement",
    "TargetMolecule",
    "VendorMetadata",
    "characterized_enzyme_catalog_digest",
    "characterized_enzyme_digest",
]
