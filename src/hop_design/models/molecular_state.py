"""Method-neutral sequence-state, lineage, pairing, and bond contracts."""

from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import JunctionPairObservation, Strand
from hop_design.models.method import BindingOrientation
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence


class EndChemistry(StrEnum):
    HYDROXYL = "hydroxyl"
    PHOSPHATE = "phosphate"


class StrandEnd(StrEnum):
    FIVE_PRIME = "five_prime"
    THREE_PRIME = "three_prime"


class LineageDirection(StrEnum):
    FORWARD = "forward"
    REVERSE = "reverse"


class LineageStrand(StrEnum):
    PRIMARY = "primary"
    COMPLEMENTARY = "complementary"


class MaterialBaseLineage(HopModel):
    """One product base traced to an input sequence and orientation."""

    product_index: int = Field(ge=0)
    origin_id: str = Field(min_length=1)
    origin_strand: LineageStrand
    origin_index: int = Field(ge=0)


class MolecularStrand(HopModel):
    """One exact linear strand stored 5-prime to 3-prime."""

    strand_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    sequence: str
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry
    lineage: tuple[MaterialBaseLineage, ...]

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_lineage(self) -> MolecularStrand:
        if len(self.lineage) != len(self.sequence):
            raise ValueError("Molecular-strand lineage must cover every base.")
        if any(item.product_index != index for index, item in enumerate(self.lineage)):
            raise ValueError("Molecular-strand lineage indexes must be contiguous.")
        return self


class Fragment(HopModel):
    """One denatured strand fragment with precursor-coordinate lineage."""

    fragment_id: str = Field(pattern=r"^(?:top|bottom)-[0-9]+-[0-9]+$")
    precursor_strand: Strand
    precursor_span: Span
    lineage_direction: LineageDirection
    sequence: str
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry
    lineage: tuple[MaterialBaseLineage, ...]

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_fragment(self) -> Fragment:
        if self.precursor_span.length.value != len(self.sequence):
            raise ValueError("Fragment span length must equal its sequence length.")
        if len(self.lineage) != len(self.sequence):
            raise ValueError("Fragment lineage must cover every base.")
        expected_direction = (
            LineageDirection.FORWARD
            if self.precursor_strand is Strand.TOP
            else LineageDirection.REVERSE
        )
        if self.lineage_direction is not expected_direction:
            raise ValueError("Fragment traversal must follow its physical strand orientation.")
        expected_origin_strand = (
            LineageStrand.PRIMARY
            if self.precursor_strand is Strand.TOP
            else LineageStrand.COMPLEMENTARY
        )
        for index, item in enumerate(self.lineage):
            expected_origin_index = (
                self.precursor_span.start.offset + index
                if self.lineage_direction is LineageDirection.FORWARD
                else self.precursor_span.end.offset - 1 - index
            )
            if (
                item.product_index != index
                or item.origin_strand is not expected_origin_strand
                or item.origin_index != expected_origin_index
            ):
                raise ValueError("Fragment lineage must replay its precursor span.")
        return self


class StrandPairObservation(JunctionPairObservation):
    """One classified pair between explicitly identified molecular strands."""

    left_strand_id: str = Field(min_length=1)
    right_strand_id: str = Field(min_length=1)


class CovalentBond(HopModel):
    """One directional phosphodiester join between strand termini."""

    upstream_strand_id: str = Field(min_length=1)
    upstream_end: StrandEnd
    downstream_strand_id: str = Field(min_length=1)
    downstream_end: StrandEnd

    @model_validator(mode="after")
    def validate_direction(self) -> CovalentBond:
        if (
            self.upstream_end is not StrandEnd.THREE_PRIME
            or self.downstream_end is not StrandEnd.FIVE_PRIME
        ):
            raise ValueError("A ligation bond must join a three-prime end to a five-prime end.")
        if self.upstream_strand_id == self.downstream_strand_id:
            raise ValueError("A pre-ligation bond must join two distinct strands.")
        return self


class PrimerBinding(HopModel):
    binding_id: str = Field(min_length=1)
    primer_id: str = Field(min_length=1)
    template_strand_id: str = Field(min_length=1)
    template_span: Span
    orientation: BindingOrientation


class SequenceProjection(HopModel):
    """One digest-addressed sequence projection from a physical product."""

    sequence: str
    sequence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_span: Span
    orientation: BindingOrientation

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_digest(self) -> SequenceProjection:
        observed = f"sha256:{hashlib.sha256(self.sequence.encode()).hexdigest()}"
        if self.sequence_digest != observed:
            raise ValueError("Sequence-projection digest must match its sequence.")
        if self.source_span.length.value != len(self.sequence):
            raise ValueError("Sequence-projection span length must match its sequence.")
        return self


class CohesiveEnd(HopModel):
    """One exact single-stranded overhang produced by a staggered digest."""

    product_end: Literal["left", "right"]
    protruding_strand_id: str = Field(min_length=1)
    overhang_end: StrandEnd
    sequence: str
    source_span: Span
    primary_cut: Boundary
    complementary_cut: Boundary

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_cut_geometry(self) -> CohesiveEnd:
        if not self.sequence:
            raise ValueError("A cohesive end must contain at least one nucleotide.")
        cut_start = min(self.primary_cut.offset, self.complementary_cut.offset)
        cut_end = max(self.primary_cut.offset, self.complementary_cut.offset)
        if self.source_span != Span(
            start=Boundary(offset=cut_start),
            end=Boundary(offset=cut_end),
        ):
            raise ValueError("Cohesive-end span must be bounded by its two strand cuts.")
        if self.source_span.length.value != len(self.sequence):
            raise ValueError("Cohesive-end span length must equal its sequence length.")
        return self


class FragmentLengthSelection(HopModel):
    """A deterministic inclusive length filter over denatured fragments."""

    min_length_nt: int = Field(ge=1)
    max_length_nt: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> FragmentLengthSelection:
        if self.max_length_nt is not None and self.max_length_nt < self.min_length_nt:
            raise ValueError("Maximum fragment length must not be below the minimum.")
        return self


class AdapterAnnealingRequest(HopModel):
    """The adapter arm and permitted physical pair classes."""

    adapter_span: Span
    max_gt_wobbles: int = Field(ge=0)
    max_hard_mismatches: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_span(self) -> AdapterAnnealingRequest:
        if self.adapter_span.start.offset != 0 or self.adapter_span.length.value == 0:
            raise ValueError("The ligating adapter arm must be a nonempty five-prime prefix.")
        return self


__all__ = [
    "AdapterAnnealingRequest",
    "CohesiveEnd",
    "CovalentBond",
    "EndChemistry",
    "Fragment",
    "FragmentLengthSelection",
    "LineageDirection",
    "LineageStrand",
    "MaterialBaseLineage",
    "MolecularStrand",
    "PrimerBinding",
    "SequenceProjection",
    "StrandEnd",
    "StrandPairObservation",
]
