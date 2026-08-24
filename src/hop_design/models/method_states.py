"""Concrete sequence-bearing states emitted by HOP method compilers."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import (
    ReleaseAgent,
    ResolvedNickSite,
    ResolvedReleaseSite,
    resolve_release_sites,
)
from hop_design.models.coordinates import Span
from hop_design.models.molecular_state import (
    CohesiveEnd,
    CovalentBond,
    Fragment,
    FragmentLengthSelection,
    MolecularStrand,
    PrimerBinding,
    SequenceProjection,
    StrandEnd,
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
    cohesive_ends: tuple[CohesiveEnd, CohesiveEnd]
    hairpin_encoding_projection: SequenceProjection
    destination_readiness: DestinationReadiness = DestinationReadiness.NOT_EVALUATED

    def assert_site_replay(self, sequence: str, *, agent: ReleaseAgent) -> None:
        """Reject product sites that do not replay the bound release agent."""
        if self.agent_id != agent.agent_id:
            raise ValueError("Restriction product must identify its bound release agent.")
        if self.sites != resolve_release_sites(sequence, agent=agent):
            raise ValueError(
                "Restriction sites must replay the bound agent across the hairpin-PCR duplex."
            )

    @model_validator(mode="after")
    def validate_cohesive_ends(self) -> RestrictionDigestProduct:
        if self.sites[0].site_span == self.sites[1].site_span:
            raise ValueError("Restriction product sites must occupy distinct physical spans.")
        if tuple(end.product_end for end in self.cohesive_ends) != ("left", "right"):
            raise ValueError("Cohesive ends must be ordered left then right.")
        strand_ids = {self.primary_strand.strand_id, self.complementary_strand.strand_id}
        if any(end.protruding_strand_id not in strand_ids for end in self.cohesive_ends):
            raise ValueError("A cohesive end must identify one product strand.")
        strands = {
            self.primary_strand.strand_id: self.primary_strand,
            self.complementary_strand.strand_id: self.complementary_strand,
        }
        for end, site in zip(self.cohesive_ends, self.sites, strict=True):
            if end.primary_cut != site.cut.top or end.complementary_cut != site.cut.bottom:
                raise ValueError("Cohesive-end cuts must replay the restriction site.")
            if end.primary_cut.offset < end.complementary_cut.offset:
                expected_overhang_end = StrandEnd.FIVE_PRIME
                expected_strand_id = (
                    self.primary_strand.strand_id
                    if end.product_end == "left"
                    else self.complementary_strand.strand_id
                )
            else:
                expected_overhang_end = StrandEnd.THREE_PRIME
                expected_strand_id = (
                    self.complementary_strand.strand_id
                    if end.product_end == "left"
                    else self.primary_strand.strand_id
                )
            if (
                end.overhang_end is not expected_overhang_end
                or end.protruding_strand_id != expected_strand_id
            ):
                raise ValueError(
                    "Cohesive-end strand and polarity must follow the staggered-cut geometry."
                )
            strand = strands[end.protruding_strand_id]
            end_length = len(end.sequence)
            expected_sequence = (
                strand.sequence[:end_length]
                if end.overhang_end is StrandEnd.FIVE_PRIME
                else strand.sequence[-end_length:]
            )
            if end.sequence != expected_sequence:
                raise ValueError("Cohesive-end sequence must match its protruding strand.")
        return self


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
