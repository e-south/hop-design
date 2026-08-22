"""Concrete sequence-bearing states emitted by HOP method compilers."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import ResolvedNickSite, ResolvedReleaseSite
from hop_design.models.coordinates import Span
from hop_design.models.molecular_state import (
    CovalentBond,
    Fragment,
    FragmentLengthSelection,
    MolecularStrand,
    PrimerBinding,
    SequenceProjection,
    StrandPairObservation,
)
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence


class DestinationReadiness(StrEnum):
    NOT_EVALUATED = "not_evaluated"


class SourcePcrDuplex(HopModel):
    state_id: Literal["source-pcr-duplex"] = "source-pcr-duplex"
    top_strand: MolecularStrand
    bottom_strand: MolecularStrand
    primer_bindings: tuple[PrimerBinding, PrimerBinding]


class MultiSiteNickedDuplex(HopModel):
    state_id: Literal["multi-site-nicked-duplex"] = "multi-site-nicked-duplex"
    top_strand: MolecularStrand
    bottom_strand: MolecularStrand
    sites: tuple[ResolvedNickSite, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_sites(self) -> MultiSiteNickedDuplex:
        length = len(self.top_strand.sequence)
        if self.bottom_strand.sequence == self.top_strand.sequence:
            raise ValueError("Nicked-duplex strands must use opposite sequence orientations.")
        keys = tuple((site.nick.strand, site.nick.boundary.offset) for site in self.sites)
        if len(keys) != len(set(keys)):
            raise ValueError("Multi-site nick events must be unique by strand and boundary.")
        if any(boundary < 0 or boundary > length for _strand, boundary in keys):
            raise ValueError("Multi-site nick boundaries must stay inside the duplex.")
        return self


class DenaturedFragmentSet(HopModel):
    state_id: Literal["denatured-fragment-set"] = "denatured-fragment-set"
    precursor_top_sequence: str
    fragments: tuple[Fragment, ...] = Field(min_length=2)

    @field_validator("precursor_top_sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_fragment_ids(self) -> DenaturedFragmentSet:
        ids = tuple(fragment.fragment_id for fragment in self.fragments)
        if len(ids) != len(set(ids)):
            raise ValueError("Denatured fragment ids must be unique.")
        return self


class LengthSelectedFragmentSet(HopModel):
    state_id: Literal["length-selected-fragment-set"] = "length-selected-fragment-set"
    selection: FragmentLengthSelection
    retained_fragment_ids: tuple[str, ...]
    excluded_fragment_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_partition(self) -> LengthSelectedFragmentSet:
        all_ids = self.retained_fragment_ids + self.excluded_fragment_ids
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("Length selection must partition unique fragment ids.")
        return self


class AdapterAnnealedComplex(HopModel):
    state_id: Literal["adapter-annealed-complex"] = "adapter-annealed-complex"
    strand_ids: tuple[str, str, str]
    pairs: tuple[StrandPairObservation, ...] = Field(min_length=1)


class LigatedHairpin(HopModel):
    state_id: Literal["ligated-hairpin"] = "ligated-hairpin"
    component_strand_ids: tuple[str, str, str]
    bonds: tuple[CovalentBond, CovalentBond]
    strand: MolecularStrand


class HairpinPcrDuplex(HopModel):
    state_id: Literal["hairpin-pcr-duplex"] = "hairpin-pcr-duplex"
    top_strand: MolecularStrand
    bottom_strand: MolecularStrand
    primer_bindings: tuple[PrimerBinding, PrimerBinding]


class RestrictionDigestProduct(HopModel):
    state_id: Literal["restriction-digest-product"] = "restriction-digest-product"
    agent_id: ReferenceId
    sites: tuple[ResolvedReleaseSite, ResolvedReleaseSite]
    primary_strand: MolecularStrand
    complementary_strand: MolecularStrand
    primary_union_span: Span
    hairpin_encoding_projection: SequenceProjection
    destination_readiness: DestinationReadiness = DestinationReadiness.NOT_EVALUATED


__all__ = [
    "AdapterAnnealedComplex",
    "DenaturedFragmentSet",
    "DestinationReadiness",
    "HairpinPcrDuplex",
    "LengthSelectedFragmentSet",
    "LigatedHairpin",
    "MultiSiteNickedDuplex",
    "RestrictionDigestProduct",
    "SourcePcrDuplex",
]
