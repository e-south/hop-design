"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/auxiliary/policy.py

Defines deterministic adapter and endpoint-primer resolution policies.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.targets import BasalPairConstraint
from hop_design.models.molecular_state import EndChemistry
from hop_design.models.sequence import normalize_dna_sequence

from ..material import ExactConstructionMaterial, MaterialResolutionMode, PcrPrimer


class AdapterPairingPolicy(HopModel):
    """Explicit distal pairs supplement, but cannot replace, the local junction."""

    distal_pairing_constraints: tuple[BasalPairConstraint, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )

    @model_validator(mode="after")
    def validate_distal_positions(self) -> AdapterPairingPolicy:
        positions = tuple(item.position_from_ligation for item in self.distal_pairing_constraints)
        if positions != tuple(sorted(set(positions))):
            raise ValueError("Distal pairing constraints require distinct ascending positions.")
        return self


class DerivedAdapterPolicy(AdapterPairingPolicy):
    """Derive the exact ligation adapter from one basal pairing authority."""

    mode: Literal[MaterialResolutionMode.DERIVE]


class ConstrainedAdapterPolicy(AdapterPairingPolicy):
    """Append one caller-supplied reusable handle to the derived pairing segment."""

    mode: Literal[MaterialResolutionMode.CONSTRAIN]
    three_prime_handle_sequence: str = Field(min_length=1)

    @field_validator("three_prime_handle_sequence", mode="before")
    @classmethod
    def normalize_handle(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Adapter handle must be a DNA string.")
        return normalize_dna_sequence(value, allow_degenerate=False)


class FixedAdapterPolicy(AdapterPairingPolicy):
    """Require one exact caller-supplied adapter material."""

    mode: Literal[MaterialResolutionMode.FIXED]
    material: ExactConstructionMaterial


type AdapterResolutionPolicy = Annotated[
    DerivedAdapterPolicy | ConstrainedAdapterPolicy | FixedAdapterPolicy,
    Field(discriminator="mode"),
]


class DerivedEndpointPrimerPolicy(HopModel):
    """Derive one terminal endpoint primer at an authored annealing length."""

    mode: Literal[MaterialResolutionMode.DERIVE]
    annealing_length_nt: int = Field(ge=1)
    five_prime_end: EndChemistry = EndChemistry.HYDROXYL


class ConstrainedEndpointPrimerPolicy(HopModel):
    """Choose the shortest terminal primer inside explicit length and handle bounds."""

    mode: Literal[MaterialResolutionMode.CONSTRAIN]
    min_annealing_length_nt: int = Field(ge=1)
    max_annealing_length_nt: int = Field(ge=1)
    five_prime_handle_sequence: str = ""
    five_prime_end: EndChemistry = EndChemistry.HYDROXYL

    @field_validator("five_prime_handle_sequence", mode="before")
    @classmethod
    def normalize_handle(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Primer handle must be a DNA string.")
        if not value:
            return ""
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_range(self) -> ConstrainedEndpointPrimerPolicy:
        if self.max_annealing_length_nt < self.min_annealing_length_nt:
            raise ValueError("Maximum primer length must not be below the minimum.")
        return self


class FixedEndpointPrimerPolicy(HopModel):
    """Require one exact caller-supplied endpoint primer."""

    mode: Literal[MaterialResolutionMode.FIXED]
    primer: PcrPrimer


type EndpointPrimerResolutionPolicy = Annotated[
    DerivedEndpointPrimerPolicy | ConstrainedEndpointPrimerPolicy | FixedEndpointPrimerPolicy,
    Field(discriminator="mode"),
]


class EndpointAuxiliaryPolicy(HopModel):
    """Resolution policies for one adapter and two PCR endpoint primers."""

    adapter: AdapterResolutionPolicy
    forward_primer: EndpointPrimerResolutionPolicy
    reverse_primer: EndpointPrimerResolutionPolicy


__all__ = [
    "AdapterResolutionPolicy",
    "ConstrainedAdapterPolicy",
    "ConstrainedEndpointPrimerPolicy",
    "DerivedAdapterPolicy",
    "DerivedEndpointPrimerPolicy",
    "EndpointAuxiliaryPolicy",
    "EndpointPrimerResolutionPolicy",
    "FixedAdapterPolicy",
    "FixedEndpointPrimerPolicy",
]
