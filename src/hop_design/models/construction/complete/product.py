"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/product.py

Defines the exact endpoint molecular product and design-sequence projection.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.realization import FinalProductReference
from hop_design.models.molecular_state import (
    CohesiveEnd,
    MolecularStrand,
    SequenceProjection,
    StrandPairObservation,
)

from .pcr import (
    DuplexFinalProductReference,
    EndpointSequenceFateSpan,
    MaterialFunctionSpan,
)


class MaterializedFinalProduct(HopModel):
    """Exact endpoint product with the encoding projection used for design comparison."""

    reference: FinalProductReference | DuplexFinalProductReference
    strands: tuple[MolecularStrand, ...] = Field(min_length=1)
    encoding_projection: SequenceProjection
    pairings: tuple[StrandPairObservation, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    cohesive_ends: tuple[CohesiveEnd, ...] = Field(default=(), exclude_if=lambda value: not value)
    material_function_spans: tuple[MaterialFunctionSpan, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    endpoint_sequence_fate_spans: tuple[EndpointSequenceFateSpan, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )

    @model_validator(mode="after")
    def validate_product(self) -> MaterializedFinalProduct:
        if self.reference.endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            if self.reference.topology != "single_stranded_hairpin" or len(self.strands) != 1:
                raise ValueError(
                    "A single-strand endpoint must preserve the exact direct ssDNA endpoint shape."
                )
            if any(
                (
                    self.pairings,
                    self.cohesive_ends,
                    self.material_function_spans,
                    self.endpoint_sequence_fate_spans,
                )
            ):
                raise ValueError("Direct ssDNA endpoint cannot contain PCR-only evidence.")
        elif self.reference.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and not isinstance(
            self.reference, DuplexFinalProductReference
        ):
            raise ValueError("Hairpin PCR endpoint requires an exact PCR duplex reference.")
        if self.reference.sequence != self.strands[0].sequence:
            raise ValueError("Final-product reference must equal its primary exact strand.")
        expected_ends = tuple(
            end.value
            for strand in self.strands
            for end in (strand.five_prime_end, strand.three_prime_end)
        )
        if self.reference.end_descriptors != expected_ends:
            raise ValueError("Final-product reference must seal exact strand-end chemistry.")
        if isinstance(self.reference, DuplexFinalProductReference) and (
            self.strands != self.reference.strands
            or self.pairings != self.reference.pairings
            or self.cohesive_ends != self.reference.cohesive_ends
        ):
            raise ValueError("PCR final product must equal its exact duplex reference graph.")
        return self


__all__ = ["MaterializedFinalProduct"]
