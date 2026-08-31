"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/spec.py

Defines exact route-material and primer contracts for complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import normalize_dna_sequence


class MaterialOrigin(StrEnum):
    """Caller-declared physical origin of one exact route material."""

    SYNTHESIZED = "synthesized"
    PCR_DERIVED = "pcr_derived"
    PURIFIED = "purified"


class ExactConstructionMaterial(HopModel):
    """One exact caller-owned material including terminal chemistry."""

    material_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    origin: MaterialOrigin
    sequence_5prime: str
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry

    @field_validator("sequence_5prime", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Construction material sequence must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)


class PcrPrimer(HopModel):
    """One exact oligo with a terminal three-prime annealing segment."""

    oligo: ExactConstructionMaterial
    annealing_length_nt: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_annealing_length(self) -> PcrPrimer:
        if self.annealing_length_nt > len(self.oligo.sequence_5prime):
            raise ValueError("Primer annealing length cannot exceed the exact oligo length.")
        return self

    @property
    def annealing_sequence(self) -> str:
        """Return the terminal three-prime segment that binds the template."""
        return self.oligo.sequence_5prime[-self.annealing_length_nt :]

    @property
    def five_prime_handle(self) -> str:
        """Return exact primer sequence outside the terminal annealing segment."""
        return self.oligo.sequence_5prime[: -self.annealing_length_nt]


class LinearSourceMaterializationSpec(HopModel):
    """Source origin/chemistry policy plus exact endpoint-dependent auxiliary oligos."""

    source_origin: MaterialOrigin
    source_five_prime_end: EndChemistry
    source_three_prime_end: EndChemistry
    source_complement_origin: MaterialOrigin
    source_complement_five_prime_end: EndChemistry
    source_complement_three_prime_end: EndChemistry
    adapter: ExactConstructionMaterial | None = None
    forward_primer: PcrPrimer | None = None
    reverse_primer: PcrPrimer | None = None

    @model_validator(mode="after")
    def validate_unique_auxiliaries(self) -> LinearSourceMaterializationSpec:
        materials = tuple(
            item
            for item in (
                self.adapter,
                None if self.forward_primer is None else self.forward_primer.oligo,
                None if self.reverse_primer is None else self.reverse_primer.oligo,
            )
            if item is not None
        )
        ids = tuple(item.material_id for item in materials)
        if len(ids) != len(set(ids)):
            raise ValueError("Construction material ids must be unique.")
        return self


__all__ = [
    "ExactConstructionMaterial",
    "LinearSourceMaterializationSpec",
    "MaterialOrigin",
    "PcrPrimer",
]
