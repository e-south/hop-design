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

from .clone.evidence import ReleasedInsertEvidence
from .pcr import (
    DuplexFinalProductReference,
    EndpointSequenceFateSpan,
    MaterialFunctionSpan,
)


class MaterializedFinalProduct(HopModel):
    """Exact endpoint product with the encoding projection used for design comparison."""

    reference: FinalProductReference | DuplexFinalProductReference
    strands: tuple[MolecularStrand, ...] = Field(min_length=1)
    encoding_projection: SequenceProjection | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    release_evidence: ReleasedInsertEvidence | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
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
        released = self.reference.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX
        if released:
            if self.encoding_projection is not None or self.release_evidence is None:
                raise ValueError(
                    "Released inserts require separate parent-core and cut-union evidence."
                )
        elif self.encoding_projection is None or self.release_evidence is not None:
            raise ValueError("Unreleased products require their endpoint encoding projection only.")
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
        elif self.reference.endpoint is ConstructionEndpoint.ADAPTER_LIGATED_HAIRPIN:
            if (
                self.reference.topology != "single_stranded_hairpin"
                or len(self.strands) != 1
                or not self.pairings
                or self.cohesive_ends
                or self.endpoint_sequence_fate_spans
            ):
                raise ValueError(
                    "Adapter hairpin requires one paired strand and no downstream ends."
                )
        elif self.reference.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and not isinstance(
            self.reference, DuplexFinalProductReference
        ):
            raise ValueError("Hairpin PCR endpoint requires an exact PCR duplex reference.")
        elif self.reference.endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX and not isinstance(
            self.reference, DuplexFinalProductReference
        ):
            raise ValueError("Clone-ready endpoint requires an exact duplex reference.")
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
            raise ValueError("Duplex final product must equal its exact reference graph.")
        return self

    @property
    def design_projection(self) -> SequenceProjection:
        """Return the core projection in its declared endpoint or pre-release parent."""
        if self.release_evidence is not None:
            return self.release_evidence.design_parent_projection
        assert self.encoding_projection is not None
        return self.encoding_projection


__all__ = ["MaterializedFinalProduct"]
