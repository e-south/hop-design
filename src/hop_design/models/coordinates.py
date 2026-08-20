"""Typed zero-based, half-open coordinate contracts."""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class Boundary(HopModel):
    """A boundary between nucleotides in a zero-based coordinate system."""

    offset: int = Field(ge=0)


class NucleotideCount(HopModel):
    """A count of nucleotides."""

    value: int = Field(ge=0)


class BasePairCount(HopModel):
    """A count of base pairs, intentionally distinct from nucleotide count."""

    value: int = Field(ge=0)


class Span(HopModel):
    """A zero-based, half-open span between two boundaries."""

    start: Boundary
    end: Boundary

    @model_validator(mode="after")
    def validate_order(self) -> Span:
        if self.end.offset < self.start.offset:
            raise ValueError("Span end boundary must not precede its start boundary.")
        return self

    @property
    def length(self) -> NucleotideCount:
        """Return the number of nucleotides covered by the span."""
        return NucleotideCount(value=self.end.offset - self.start.offset)

    def contains_index(self, index: int) -> bool:
        """Return whether a zero-based nucleotide index lies inside the span."""
        return self.start.offset <= index < self.end.offset
