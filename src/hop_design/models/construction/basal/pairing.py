"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/pairing.py

Defines exact basal construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    BasalPairClass,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    characterized_enzyme_digest,
)
from hop_design.models.junction import Strand
from hop_design.models.physical import JunctionPairKind, classify_literal_pair
from hop_design.models.sequence import (
    normalize_dna_sequence,
)


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


class BasalBoundaryControl(HopModel):
    """The exact basal nick boundary and its binding authority."""

    strand: Strand
    boundary: Boundary
    enzyme_id: str
    binding_id: str
