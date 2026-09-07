"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/basal/states.py

Defines exact basal construction evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction import (
    ConstructionEndpoint,
)
from hop_design.models.sequence import (
    normalize_dna_sequence,
    reverse_complement_iupac,
)

from .pairing import BasalPairingState


class BasalAnnealingObligation(HopModel):
    """Required full adapter annealing extent derived from one proximal pairing state."""

    proximal_annealing_nt: int = Field(ge=1)
    minimum_annealing_nt: int = Field(ge=1)
    required_annealing_nt: int = Field(ge=1)
    annealing_completion_nt: int = Field(ge=0)
    mismatch_count: int = Field(ge=0)
    mismatch_fraction: float = Field(ge=0.0, le=1.0)
    mismatch_warning_fraction: float = Field(ge=0.0, le=1.0)
    warnings: tuple[Literal["mismatch-fraction-above-threshold"], ...] = ()

    @classmethod
    def create(
        cls,
        *,
        pairing_state: BasalPairingState,
        minimum_annealing_nt: int,
        mismatch_warning_fraction: float,
    ) -> BasalAnnealingObligation:
        """Derive one annealing obligation without inventing completion bases."""
        proximal = len(pairing_state.pairs)
        required = max(proximal, minimum_annealing_nt)
        mismatches = sum(pair.pair_class.value == "mismatch" for pair in pairing_state.pairs)
        mismatch_fraction = mismatches / required
        warnings: tuple[Literal["mismatch-fraction-above-threshold"], ...] = (
            ("mismatch-fraction-above-threshold",)
            if mismatch_fraction > mismatch_warning_fraction
            else ()
        )
        return cls(
            proximal_annealing_nt=proximal,
            minimum_annealing_nt=minimum_annealing_nt,
            required_annealing_nt=required,
            annealing_completion_nt=required - proximal,
            mismatch_count=mismatches,
            mismatch_fraction=mismatch_fraction,
            mismatch_warning_fraction=mismatch_warning_fraction,
            warnings=warnings,
        )

    @model_validator(mode="after")
    def validate_obligation(self) -> BasalAnnealingObligation:
        required = max(self.proximal_annealing_nt, self.minimum_annealing_nt)
        fraction = self.mismatch_count / required
        warnings = (
            ("mismatch-fraction-above-threshold",)
            if fraction > self.mismatch_warning_fraction
            else ()
        )
        if (
            self.required_annealing_nt != required
            or self.annealing_completion_nt != required - self.proximal_annealing_nt
            or self.mismatch_count > self.proximal_annealing_nt
            or self.mismatch_fraction != fraction
            or self.warnings != warnings
        ):
            raise ValueError("Basal annealing obligation must derive from its exact counts.")
        return self


class BasalBoundaryProjection(HopModel):
    """Exact local sequence and upstream obligations at one basal boundary."""

    endpoint: Literal[
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    ]
    pairing_state: BasalPairingState
    annealing_obligation: BasalAnnealingObligation
    local_reference_sequence: str
    local_complement_sequence: str

    @field_validator("local_reference_sequence", "local_complement_sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Basal boundary sequences must be DNA strings.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_boundary(self) -> BasalBoundaryProjection:
        if (
            reverse_complement_iupac(self.local_reference_sequence)
            != self.local_complement_sequence
        ):
            raise ValueError("The local complement must derive from the local reference.")
        if not self.local_reference_sequence.endswith(self.pairing_state.adapter_sequence_5prime):
            raise ValueError("The local reference must end with the constrained adapter segment.")
        expected = BasalAnnealingObligation.create(
            pairing_state=self.pairing_state,
            minimum_annealing_nt=self.annealing_obligation.minimum_annealing_nt,
            mismatch_warning_fraction=self.annealing_obligation.mismatch_warning_fraction,
        )
        if self.annealing_obligation != expected:
            raise ValueError("Basal annealing obligation must replay its proximal pairing state.")
        return self
