"""Authored payload contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
    reverse_complement_iupac,
)


class ExactPayload(HopModel):
    """A payload whose sequence contains only A, C, G, and T."""

    kind: Literal["exact"] = "exact"
    sequence: str

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @property
    def paired_sequence(self) -> str:
        """The derived paired arm; it is never independently authored."""
        return reverse_complement_iupac(self.sequence)


class DegeneratePayload(HopModel):
    """A symbolic payload using the complete DNA IUPAC alphabet."""

    kind: Literal["degenerate"] = "degenerate"
    sequence: str

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)

    @property
    def paired_sequence(self) -> str:
        """The symbolic IUPAC reverse complement of the authored payload."""
        return reverse_complement_iupac(self.sequence)


Payload = Annotated[ExactPayload | DegeneratePayload, Field(discriminator="kind")]
