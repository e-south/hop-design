"""Annealing and restriction-product helpers for the linear-source method."""

from __future__ import annotations

from typing import Literal

from hop_design.kernel.molecular_states import build_lineage, observe_pair, reindex_lineage
from hop_design.kernel.site_scanning import scan_release_agent
from hop_design.models.catalog import SiteOrientation
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.linear_source_method import LinearSourceMultinickHairpinPcrRequest
from hop_design.models.method import BindingOrientation
from hop_design.models.method_states import HairpinPcrDuplex, RestrictionDigestProduct
from hop_design.models.molecular_state import (
    CohesiveEnd,
    EndChemistry,
    Fragment,
    LineageStrand,
    MolecularStrand,
    SequenceProjection,
    StrandEnd,
    StrandPairObservation,
)
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import sha256_digest


def resolve_selected_pairs(
    top: Fragment,
    bottom: Fragment,
    adapter: MolecularStrand,
    request: LinearSourceMultinickHairpinPcrRequest,
) -> tuple[StrandPairObservation, ...] | None:
    overlap_start = max(top.precursor_span.start.offset, bottom.precursor_span.start.offset)
    overlap_end = min(top.precursor_span.end.offset, bottom.precursor_span.end.offset)
    if overlap_start >= overlap_end:
        return None
    retained_pairs = tuple(
        observe_pair(
            left_strand_id=top.fragment_id,
            right_strand_id=bottom.fragment_id,
            left_index=coordinate - top.precursor_span.start.offset,
            right_index=bottom.precursor_span.end.offset - 1 - coordinate,
            left_base=top.sequence[coordinate - top.precursor_span.start.offset],
            right_base=bottom.sequence[bottom.precursor_span.end.offset - 1 - coordinate],
        )
        for coordinate in range(overlap_start, overlap_end)
    )
    arm = request.adapter_annealing.adapter_span
    adapter_start = overlap_start - arm.length.value
    if adapter_start < top.precursor_span.start.offset:
        return None
    adapter_pairs = tuple(
        observe_pair(
            left_strand_id=top.fragment_id,
            right_strand_id=adapter.strand_id,
            left_index=adapter_start + position - top.precursor_span.start.offset,
            right_index=arm.end.offset - 1 - position,
            left_base=top.sequence[adapter_start + position - top.precursor_span.start.offset],
            right_base=adapter.sequence[arm.end.offset - 1 - position],
        )
        for position in range(arm.length.value)
    )
    return retained_pairs + adapter_pairs


def build_restriction_product(
    request: LinearSourceMultinickHairpinPcrRequest,
    duplex: HairpinPcrDuplex,
) -> RestrictionDigestProduct | None:
    sites = scan_release_agent(duplex.top_strand.sequence, agent=request.restriction_agent)
    if len(sites) != 2 or tuple(site.orientation for site in sites) != (
        SiteOrientation.FORWARD,
        SiteOrientation.REVERSE,
    ):
        return None
    left, right = sites
    top_start, top_end = left.cut.top.offset, right.cut.top.offset
    bottom_start, bottom_end = left.cut.bottom.offset, right.cut.bottom.offset
    if not (top_start < top_end and bottom_start < bottom_end):
        return None
    union = Span(
        start=Boundary(offset=min(top_start, bottom_start)),
        end=Boundary(offset=max(top_end, bottom_end)),
    )
    primary = MolecularStrand(
        strand_id="restriction-primary",
        sequence=duplex.top_strand.sequence[top_start:top_end],
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=reindex_lineage((duplex.top_strand.lineage[top_start:top_end],)),
    )
    complementary = MolecularStrand(
        strand_id="restriction-complementary",
        sequence=reverse_complement_iupac(duplex.top_strand.sequence[bottom_start:bottom_end]),
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=build_lineage(
            origin_id=duplex.top_strand.strand_id,
            origin_strand=LineageStrand.COMPLEMENTARY,
            origin_indexes=range(bottom_end - 1, bottom_start - 1, -1),
        ),
    )
    union_sequence = duplex.top_strand.sequence[union.start.offset : union.end.offset]
    projected = (
        union_sequence
        if request.hairpin_encoding_projection_orientation is BindingOrientation.SAME_5TO3
        else reverse_complement_iupac(union_sequence)
    )
    left_end = _build_cohesive_end(
        product_end="left",
        top_sequence=duplex.top_strand.sequence,
        primary_cut=left.cut.top,
        complementary_cut=left.cut.bottom,
        primary_strand_id=primary.strand_id,
        complementary_strand_id=complementary.strand_id,
    )
    right_end = _build_cohesive_end(
        product_end="right",
        top_sequence=duplex.top_strand.sequence,
        primary_cut=right.cut.top,
        complementary_cut=right.cut.bottom,
        primary_strand_id=primary.strand_id,
        complementary_strand_id=complementary.strand_id,
    )
    if left_end is None or right_end is None:
        return None
    return RestrictionDigestProduct(
        agent_id=request.restriction_agent.agent_id,
        sites=sites,
        primary_strand=primary,
        complementary_strand=complementary,
        primary_union_span=union,
        cohesive_ends=(left_end, right_end),
        hairpin_encoding_projection=SequenceProjection(
            sequence=projected,
            sequence_digest=sha256_digest(projected.encode()),
            source_span=union,
            orientation=request.hairpin_encoding_projection_orientation,
        ),
    )


def _build_cohesive_end(
    *,
    product_end: Literal["left", "right"],
    top_sequence: str,
    primary_cut: Boundary,
    complementary_cut: Boundary,
    primary_strand_id: str,
    complementary_strand_id: str,
) -> CohesiveEnd | None:
    """Derive one exact overhang from aligned top-strand cut coordinates."""
    primary_offset = primary_cut.offset
    complementary_offset = complementary_cut.offset
    if primary_offset == complementary_offset:
        return None
    span = Span(
        start=Boundary(offset=min(primary_offset, complementary_offset)),
        end=Boundary(offset=max(primary_offset, complementary_offset)),
    )
    aligned_sequence = top_sequence[span.start.offset : span.end.offset]
    if primary_offset < complementary_offset:
        protruding_strand_id = (
            primary_strand_id if product_end == "left" else complementary_strand_id
        )
        sequence = (
            aligned_sequence
            if product_end == "left"
            else reverse_complement_iupac(aligned_sequence)
        )
        overhang_end = StrandEnd.FIVE_PRIME
    else:
        protruding_strand_id = (
            complementary_strand_id if product_end == "left" else primary_strand_id
        )
        sequence = (
            reverse_complement_iupac(aligned_sequence)
            if product_end == "left"
            else aligned_sequence
        )
        overhang_end = StrandEnd.THREE_PRIME
    return CohesiveEnd(
        product_end=product_end,
        protruding_strand_id=protruding_strand_id,
        overhang_end=overhang_end,
        sequence=sequence,
        source_span=span,
        primary_cut=primary_cut,
        complementary_cut=complementary_cut,
    )


__all__ = ["build_restriction_product", "resolve_selected_pairs"]
