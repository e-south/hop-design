"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/policy.py

Defines deterministic source-material and primer resolution policies.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import normalize_dna_sequence

from ..material import ExactConstructionMaterial, MaterialResolutionMode, PcrPrimer


class DerivedSourceSsdnaPolicy(HopModel):
    """Derive the exact source ssDNA from the selected route sequence."""

    mode: Literal[MaterialResolutionMode.DERIVE]
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry


class FixedSourceSsdnaPolicy(HopModel):
    """Require one exact caller-supplied source ssDNA specification."""

    mode: Literal[MaterialResolutionMode.FIXED]
    material: ExactConstructionMaterial


class ConstrainedSourceSsdnaPolicy(HopModel):
    """Search an authored upstream IUPAC context without changing local junctions."""

    mode: Literal[MaterialResolutionMode.CONSTRAIN]
    upstream_sequence_spec: str
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry

    @field_validator("upstream_sequence_spec", mode="before")
    @classmethod
    def normalize_context(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Upstream sequence specification must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=True)


type SourceSsdnaPolicy = Annotated[
    DerivedSourceSsdnaPolicy | ConstrainedSourceSsdnaPolicy | FixedSourceSsdnaPolicy,
    Field(discriminator="mode"),
]


class DerivedPrimerPolicy(HopModel):
    """Derive one exact terminal primer at an authored annealing length."""

    mode: Literal[MaterialResolutionMode.DERIVE]
    annealing_length_nt: int = Field(ge=1)


class ConstrainedPrimerPolicy(HopModel):
    """Choose the shortest terminal primer inside one explicit length range."""

    mode: Literal[MaterialResolutionMode.CONSTRAIN]
    min_annealing_length_nt: int = Field(ge=1)
    max_annealing_length_nt: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> ConstrainedPrimerPolicy:
        if self.max_annealing_length_nt < self.min_annealing_length_nt:
            raise ValueError("Maximum primer length must not be below the minimum.")
        return self


class FixedPrimerPolicy(HopModel):
    """Require one exact caller-supplied primer specification."""

    mode: Literal[MaterialResolutionMode.FIXED]
    primer: PcrPrimer


type PrimerResolutionPolicy = Annotated[
    DerivedPrimerPolicy | ConstrainedPrimerPolicy | FixedPrimerPolicy,
    Field(discriminator="mode"),
]


class SourceDuplexPreparationPolicy(HopModel):
    """Resolution policy for the external roots of one source-copying stage."""

    source_ssdna: SourceSsdnaPolicy
    forward_primer: PrimerResolutionPolicy
    reverse_primer: PrimerResolutionPolicy


__all__ = [
    "ConstrainedPrimerPolicy",
    "ConstrainedSourceSsdnaPolicy",
    "DerivedPrimerPolicy",
    "DerivedSourceSsdnaPolicy",
    "FixedPrimerPolicy",
    "FixedSourceSsdnaPolicy",
    "PrimerResolutionPolicy",
    "SourceDuplexPreparationPolicy",
    "SourceSsdnaPolicy",
]
