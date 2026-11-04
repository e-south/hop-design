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


class UpstreamSequenceLengthRange(HopModel):
    """Bound upstream lengths and the IUPAC base domain at every position."""

    min_length_nt: int = Field(ge=1)
    max_length_nt: int = Field(ge=1, le=1_000)
    base_spec: str = Field(min_length=1, max_length=1)

    @field_validator("base_spec")
    @classmethod
    def normalize_base(cls, value: str) -> str:
        return normalize_dna_sequence(value, allow_degenerate=True)

    @model_validator(mode="after")
    def validate_range(self) -> UpstreamSequenceLengthRange:
        if self.max_length_nt < self.min_length_nt:
            raise ValueError("Maximum upstream length must not be below the minimum.")
        return self


class ConstrainedSourceSsdnaPolicy(HopModel):
    """Search an authored upstream IUPAC context without changing local junctions."""

    mode: Literal[MaterialResolutionMode.CONSTRAIN]
    upstream_sequence_spec: str | UpstreamSequenceLengthRange
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry

    @field_validator("upstream_sequence_spec", mode="before")
    @classmethod
    def normalize_context(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_dna_sequence(value, allow_degenerate=True)
        return value


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


def primer_required_length(policy: PrimerResolutionPolicy) -> int:
    """Shortest permitted binding footprint, independently of available source geometry."""
    if isinstance(policy, FixedPrimerPolicy):
        return policy.primer.annealing_length_nt
    if isinstance(policy, DerivedPrimerPolicy):
        return policy.annealing_length_nt
    return policy.min_annealing_length_nt


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
    "UpstreamSequenceLengthRange",
    "primer_required_length",
]
