"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/pairing.py

Defines exact basal construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    BasalPairClass,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeClass,
    EnzymeRole,
    characterized_enzyme_digest,
)
from hop_design.models.junction import Strand
from hop_design.models.physical import JunctionPairKind, SiteOrientation, classify_literal_pair
from hop_design.models.sequence import (
    iupac_bases,
    normalize_dna_sequence,
    reverse_complement_iupac,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest


def derive_basal_pair_class(source_base: str, adapter_base: str) -> BasalPairClass:
    """Classify one exact source-adapter pair from its literal bases."""
    return {
        JunctionPairKind.WATSON_CRICK: BasalPairClass.MATCH,
        JunctionPairKind.GT_WOBBLE: BasalPairClass.WOBBLE,
        JunctionPairKind.HARD_MISMATCH: BasalPairClass.MISMATCH,
    }[classify_literal_pair(left_base=source_base, right_base=adapter_base)]


class BasalPairRecord(HopModel):
    """One literal pair in payload-proximal-to-outward physical order."""

    profile_position: int = Field(ge=0)
    source_index: int = Field(ge=0)
    adapter_index: int = Field(ge=0)
    source_base: str
    adapter_base: str
    pair_class: BasalPairClass
    compact_symbol: Literal["M", "W", "X"]
    participates_in_end_projection: bool = False

    @field_validator("source_base", "adapter_base", mode="before")
    @classmethod
    def normalize_base(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Basal pair bases must be DNA strings.")
        normalized = normalize_dna_sequence(value, allow_degenerate=False)
        if len(normalized) != 1:
            raise ValueError("Basal pair bases must contain exactly one nucleotide.")
        return normalized

    @model_validator(mode="after")
    def validate_projection(self) -> BasalPairRecord:
        expected_class = derive_basal_pair_class(self.source_base, self.adapter_base)
        if self.pair_class is not expected_class:
            raise ValueError("The basal pair class must derive from the literal bases.")
        expected_symbol = {
            BasalPairClass.MATCH: "M",
            BasalPairClass.WOBBLE: "W",
            BasalPairClass.MISMATCH: "X",
        }[self.pair_class]
        if self.compact_symbol != expected_symbol:
            raise ValueError("The compact basal symbol must derive from the literal pair class.")
        return self


class BasalPairingProfile(HopModel):
    """Exact antiparallel arms and their literal M/W/X evidence."""

    source_sequence_5prime: str
    adapter_sequence_5prime: str
    source_span: Span
    adapter_span: Span
    pairs: tuple[BasalPairRecord, ...] = Field(min_length=1)
    compact_profile: str = Field(pattern=r"^[MWX]+$")

    @field_validator("source_sequence_5prime", "adapter_sequence_5prime", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Basal pairing sequences must be DNA strings.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_pairing(self) -> BasalPairingProfile:
        length = len(self.source_sequence_5prime)
        if not length or len(self.adapter_sequence_5prime) != length:
            raise ValueError("Basal pairing arms must have equal nonzero length.")
        if self.source_span.length.value != length or self.adapter_span.length.value != length:
            raise ValueError("Basal pairing spans must equal their exact arm lengths.")
        if len(self.pairs) != length:
            raise ValueError("Basal pair records must cover both pairing arms exactly.")
        for position, pair in enumerate(self.pairs):
            source_index = length - 1 - position
            if (pair.profile_position, pair.source_index, pair.adapter_index) != (
                position,
                source_index,
                position,
            ):
                raise ValueError("Basal pair records must use proximal-outward coordinates.")
            if (
                pair.source_base != self.source_sequence_5prime[source_index]
                or pair.adapter_base != self.adapter_sequence_5prime[position]
            ):
                raise ValueError("Basal pair records must replay the exact pairing arms.")
        if self.compact_profile != "".join(pair.compact_symbol for pair in self.pairs):
            raise ValueError("The M/W/X profile must replay every literal basal pair.")
        return self


class BasalEnzymeDefinition(HopModel):
    """One characterized definition and its procurement-independent digest."""

    enzyme_id: str
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    enzyme: CharacterizedEnzyme

    @model_validator(mode="after")
    def validate_definition(self) -> BasalEnzymeDefinition:
        if self.enzyme_id != self.enzyme.enzyme_id or self.digest != characterized_enzyme_digest(
            self.enzyme
        ):
            raise ValueError("Basal enzyme definition and digest must seal the enzyme.")
        return self


class BasalEnzymeBinding(HopModel):
    """One exact recognition placement and operative cut geometry."""

    binding_id: str = Field(pattern=r"^hop:enzyme-binding/[0-9a-f]{64}@1$")
    enzyme_id: str
    role: EnzymeRole
    strand: Strand | None
    recognition_span: Span
    orientation: SiteOrientation
    reference_cut: Boundary | None
    complement_cut: Boundary | None

    @classmethod
    def create(
        cls,
        *,
        enzyme_id: str,
        role: EnzymeRole,
        strand: Strand | None,
        recognition_span: Span,
        orientation: SiteOrientation,
        reference_cut: Boundary | None,
        complement_cut: Boundary | None,
    ) -> BasalEnzymeBinding:
        facts: dict[str, object] = {
            "enzyme_id": enzyme_id,
            "role": role,
            "strand": strand,
            "recognition_span": recognition_span,
            "orientation": orientation,
            "reference_cut": reference_cut,
            "complement_cut": complement_cut,
        }
        content = cls._content(facts)
        digest = sha256_digest(canonical_json_bytes(content)).removeprefix("sha256:")
        return cls.model_validate({"binding_id": f"hop:enzyme-binding/{digest}@1", **facts})

    @staticmethod
    def _content(facts: dict[str, object]) -> dict[str, object]:
        return {
            key: (
                value.model_dump(mode="json")
                if isinstance(value, HopModel)
                else value.value
                if isinstance(value, StrEnum)
                else value
            )
            for key, value in facts.items()
        }

    @model_validator(mode="after")
    def validate_binding(self) -> BasalEnzymeBinding:
        facts = self.model_dump(mode="json", exclude={"binding_id"})
        digest = sha256_digest(canonical_json_bytes(facts)).removeprefix("sha256:")
        if self.binding_id != f"hop:enzyme-binding/{digest}@1":
            raise ValueError("Basal binding identity must seal its exact placement and cuts.")
        operative = self.reference_cut if self.strand is Strand.TOP else self.complement_cut
        if self.role is EnzymeRole.BASAL_NICK and operative is None:
            raise ValueError("Basal nick binding must cut its controlled strand.")
        if self.role is EnzymeRole.END_GENERATION and (
            self.reference_cut is None or self.complement_cut is None
        ):
            raise ValueError("End generation requires two exact strand cuts.")
        return self

    def assert_definition_replay(
        self,
        *,
        enzyme: CharacterizedEnzyme,
        sequence: str,
    ) -> None:
        """Replay one embedded definition against its exact placement and cuts."""
        if self.enzyme_id != enzyme.enzyme_id:
            raise ValueError("Basal binding must reference its embedded enzyme definition.")
        if self.role is EnzymeRole.BASAL_NICK:
            if enzyme.enzyme_class is not EnzymeClass.NICKASE:
                raise ValueError("Basal nick bindings require a characterized nickase.")
        elif enzyme.enzyme_class is not EnzymeClass.DUPLEX_RESTRICTION:
            raise ValueError("End-generation bindings require a duplex restriction enzyme.")
        pattern = (
            enzyme.recognition_pattern
            if self.orientation is SiteOrientation.FORWARD
            else reverse_complement_iupac(enzyme.recognition_pattern)
        )
        observed = sequence[self.recognition_span.start.offset : self.recognition_span.end.offset]
        if len(observed) != len(pattern) or any(
            base not in iupac_bases(symbol) for base, symbol in zip(observed, pattern, strict=True)
        ):
            raise ValueError("Basal binding recognition must replay its enzyme definition.")
        start = self.recognition_span.start.offset
        if self.orientation is SiteOrientation.FORWARD:
            reference_offset = enzyme.cut_offset_reference_strand
            complement_offset = enzyme.cut_offset_complement_strand
        elif enzyme.enzyme_class is EnzymeClass.NICKASE:
            reference_offset = None
            complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
        else:
            if enzyme.cut_offset_complement_strand is None:
                raise ValueError("End-generation definitions require two cut offsets.")
            reference_offset = enzyme.recognition_length - enzyme.cut_offset_complement_strand
            complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
        expected_reference = (
            Boundary(offset=start + reference_offset) if reference_offset is not None else None
        )
        expected_complement = (
            Boundary(offset=start + complement_offset) if complement_offset is not None else None
        )
        if self.reference_cut != expected_reference or self.complement_cut != expected_complement:
            raise ValueError("Basal binding cuts must replay its enzyme definition.")


class BasalBoundaryControl(HopModel):
    """The exact basal nick boundary and its binding authority."""

    strand: Strand
    boundary: Boundary
    enzyme_id: str
    binding_id: str
