"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pcr/authority.py

Defines exact adapter and primer-extension authorities for PCR endpoints.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import ConstructionEndpoint, _content_id
from hop_design.models.coordinates import Span
from hop_design.models.method import BindingOrientation
from hop_design.models.molecular_state import (
    CohesiveEnd,
    CovalentBond,
    MolecularStrand,
    PrimerBinding,
    StrandPairObservation,
)

from ..material import ExactConstructionMaterial, PcrPrimer


class MaterialFunction(StrEnum):
    """Closed biochemical functions assigned to exact input-material spans."""

    SOURCE_REFERENCE = "source_reference"
    SOURCE_COMPLEMENT = "source_complement"
    ADAPTER = "adapter"
    FORWARD_PRIMER = "forward_primer"
    REVERSE_PRIMER = "reverse_primer"


class EndpointSequenceFate(StrEnum):
    """Closed endpoint roles assigned independently from material function."""

    PAYLOAD = "payload"
    RETAINED_CONSTRUCTION = "retained_construction"
    TRANSIENT_CONSTRUCTION = "transient_construction"
    DESTINATION_ASSOCIATED = "destination_associated"


class EndpointStrand(StrEnum):
    """Ordered endpoint duplex strands."""

    TOP = "top"
    BOTTOM = "bottom"


class MaterialFunctionSpan(HopModel):
    """One exact input-material span and the molecular function it supplies."""

    material_id: str = Field(min_length=1)
    function: MaterialFunction
    material_span: Span
    endpoint_strand: EndpointStrand
    endpoint_span: Span
    orientation: BindingOrientation

    @model_validator(mode="after")
    def validate_lengths(self) -> MaterialFunctionSpan:
        if self.material_span.length != self.endpoint_span.length:
            raise ValueError("Material-function mapping must preserve exact span length.")
        return self


class EndpointSequenceFateSpan(HopModel):
    """One endpoint span classified by its sequence fate in the final product."""

    endpoint_strand: EndpointStrand
    endpoint_span: Span
    fate: EndpointSequenceFate


class AdapterAnnealingAuthority(HopModel):
    """Exact adapter material, binding spans, and literal pair associations."""

    authority_id: str = Field(pattern=r"^hop:adapter-annealing/[0-9a-f]{64}@1$")
    pre_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    post_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    adapter: ExactConstructionMaterial
    hairpin_span: Span
    adapter_span: Span
    pairings: tuple[StrandPairObservation, ...] = Field(min_length=1)

    @classmethod
    def create(cls, **content: object) -> AdapterAnnealingAuthority:
        draft = cls.model_construct(authority_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"authority_id"})
        return cls.model_validate(
            {"authority_id": _content_id("adapter-annealing", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_identity(self) -> AdapterAnnealingAuthority:
        content = self.model_dump(mode="json", exclude={"authority_id"})
        if self.authority_id != _content_id("adapter-annealing", 1, content):
            raise ValueError("Adapter-annealing identity must seal its exact evidence.")
        if self.hairpin_span.length != self.adapter_span.length or (
            self.adapter_span.length.value != len(self.pairings)
        ):
            raise ValueError("Adapter annealing must pair both declared spans completely.")
        return self


class AdapterLigationAuthority(HopModel):
    """Exact adapter ligation relation and phosphodiester bond."""

    authority_id: str = Field(pattern=r"^hop:adapter-ligation/[0-9a-f]{64}@1$")
    pre_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    post_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    adapter: ExactConstructionMaterial
    bond: CovalentBond
    product: MolecularStrand

    @classmethod
    def create(cls, **content: object) -> AdapterLigationAuthority:
        draft = cls.model_construct(authority_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"authority_id"})
        return cls.model_validate(
            {"authority_id": _content_id("adapter-ligation", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_identity(self) -> AdapterLigationAuthority:
        content = self.model_dump(mode="json", exclude={"authority_id"})
        if self.authority_id != _content_id("adapter-ligation", 1, content):
            raise ValueError("Adapter-ligation identity must seal its exact product.")
        return self


class PrimerExtensionAuthority(HopModel):
    """Exact primer bindings and copied duplex produced from one ligated template."""

    authority_id: str = Field(pattern=r"^hop:primer-extension/[0-9a-f]{64}@1$")
    pre_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    post_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    forward_primer: PcrPrimer
    reverse_primer: PcrPrimer
    bindings: tuple[PrimerBinding, PrimerBinding]
    products: tuple[MolecularStrand, MolecularStrand]
    pairings: tuple[StrandPairObservation, ...] = Field(min_length=1)
    material_function_spans: tuple[MaterialFunctionSpan, ...] = Field(min_length=2)
    endpoint_sequence_fate_spans: tuple[EndpointSequenceFateSpan, ...] = Field(min_length=4)

    @classmethod
    def create(cls, **content: object) -> PrimerExtensionAuthority:
        draft = cls.model_construct(authority_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"authority_id"})
        return cls.model_validate(
            {"authority_id": _content_id("primer-extension", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_identity(self) -> PrimerExtensionAuthority:
        content = self.model_dump(mode="json", exclude={"authority_id"})
        if self.authority_id != _content_id("primer-extension", 1, content):
            raise ValueError("Primer-extension identity must seal exact copied products.")
        primer_ids = (
            self.forward_primer.oligo.material_id,
            self.reverse_primer.oligo.material_id,
        )
        if tuple(item.primer_id for item in self.bindings) != primer_ids:
            raise ValueError("Primer bindings must preserve exact declared primer order.")
        if not {
            MaterialFunction.FORWARD_PRIMER,
            MaterialFunction.REVERSE_PRIMER,
        }.issubset(item.function for item in self.material_function_spans):
            raise ValueError("Material-function spans must retain both exact primer roles.")
        by_strand: dict[EndpointStrand, list[Span]] = {strand: [] for strand in EndpointStrand}
        for item in self.endpoint_sequence_fate_spans:
            by_strand[item.endpoint_strand].append(item.endpoint_span)
        for spans in by_strand.values():
            cursor = 0
            for span in spans:
                if span.start.offset != cursor or span.end.offset <= cursor:
                    raise ValueError("Endpoint-fate spans must be ordered and nonoverlapping.")
                cursor = span.end.offset
        if tuple(spans[-1].end.offset if spans else -1 for spans in by_strand.values()) != (
            len(self.products[0].sequence),
            len(self.products[1].sequence),
        ):
            raise ValueError("Endpoint-fate spans must cover both complete PCR strands.")
        return self


PcrTransitionAuthority = (
    AdapterAnnealingAuthority | AdapterLigationAuthority | PrimerExtensionAuthority
)


class DuplexFinalProductReference(HopModel):
    """Exact content address over both duplex strands and their molecular graph."""

    final_product_id: str = Field(pattern=r"^hop:final-product/[0-9a-f]{64}@1$")
    endpoint: Literal[
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    ]
    sequence: str
    topology: Literal["linear_duplex"] = "linear_duplex"
    end_descriptors: tuple[str, str, str, str]
    strands: tuple[MolecularStrand, MolecularStrand]
    pairings: tuple[StrandPairObservation, ...] = Field(min_length=1)
    cohesive_ends: tuple[CohesiveEnd, ...] = ()

    @classmethod
    def create(cls, **content: object) -> DuplexFinalProductReference:
        draft = cls.model_construct(final_product_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"final_product_id"})
        return cls.model_validate(
            {"final_product_id": _content_id("final-product", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_identity(self) -> DuplexFinalProductReference:
        content = self.model_dump(mode="json", exclude={"final_product_id"})
        if self.final_product_id != _content_id("final-product", 1, content):
            raise ValueError("Duplex product identity must seal the complete molecular graph.")
        if self.sequence != self.strands[0].sequence:
            raise ValueError("Duplex reference sequence must equal the ordered top strand.")
        expected_ends = tuple(
            end.value
            for strand in self.strands
            for end in (strand.five_prime_end, strand.three_prime_end)
        )
        if self.end_descriptors != expected_ends:
            raise ValueError("Duplex product must seal exact strand-end chemistry.")
        if self.endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            if self.cohesive_ends:
                raise ValueError("PCR product must preserve exact blunt ends.")
        elif tuple(end.product_end for end in self.cohesive_ends) != ("left", "right"):
            raise ValueError("Clone-ready product must preserve left and right cohesive ends.")
        return self


__all__ = [
    "AdapterAnnealingAuthority",
    "AdapterLigationAuthority",
    "DuplexFinalProductReference",
    "EndpointSequenceFate",
    "EndpointSequenceFateSpan",
    "EndpointStrand",
    "MaterialFunction",
    "MaterialFunctionSpan",
    "PcrTransitionAuthority",
    "PrimerExtensionAuthority",
]
