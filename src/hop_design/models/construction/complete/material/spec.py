"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/spec.py

Defines exact route-material and primer contracts for complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import normalize_dna_sequence

from .identity import construction_material_id


class MaterialResolutionMode(StrEnum):
    """How one exact route material specification was resolved."""

    DERIVE = "derive"
    CONSTRAIN = "constrain"
    FIXED = "fixed"


class ExactConstructionMaterial(HopModel):
    """One exact molecular material specification including terminal chemistry."""

    material_id: str = Field(pattern=r"^hop:construction-material/[0-9a-f]{64}@1$")
    polymer_type: Literal["DNA"] = "DNA"
    strandedness: Literal["single_stranded"] = "single_stranded"
    topology: Literal["linear"] = "linear"
    sequence_5prime: str
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry

    @model_validator(mode="before")
    @classmethod
    def seal_content_identity(cls, value: object) -> object:
        if isinstance(value, cls) or not isinstance(value, Mapping):
            return value
        content = dict(value)
        required = {"sequence_5prime", "five_prime_end", "three_prime_end"}
        if not required.issubset(content):
            return value
        expected = construction_material_id(
            content["sequence_5prime"],
            five_prime_end=content["five_prime_end"],
            three_prime_end=content["three_prime_end"],
            polymer_type=content.get("polymer_type", "DNA"),
            strandedness=content.get("strandedness", "single_stranded"),
            topology=content.get("topology", "linear"),
        )
        supplied = content.get("material_id")
        if supplied is not None and supplied != expected:
            raise ValueError("Construction material id must equal its molecular content identity.")
        content["material_id"] = expected
        return content

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


__all__ = [
    "ExactConstructionMaterial",
    "MaterialResolutionMode",
    "PcrPrimer",
]
