"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/molecular_replay.py

Replays strand lineage, denatured fragments, and physical base-pair observations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from itertools import pairwise

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import (
    EndChemistry,
    Fragment,
    LineageDirection,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.physical import classify_literal_pair
from hop_design.models.sequence import reverse_complement_iupac


def build_lineage(
    *,
    origin_id: str,
    origin_strand: LineageStrand,
    origin_indexes: Iterable[int],
) -> tuple[MaterialBaseLineage, ...]:
    return tuple(
        MaterialBaseLineage(
            product_index=product_index,
            origin_id=origin_id,
            origin_strand=origin_strand,
            origin_index=origin_index,
        )
        for product_index, origin_index in enumerate(origin_indexes)
    )


def reindex_lineage(
    groups: Sequence[tuple[MaterialBaseLineage, ...]],
) -> tuple[MaterialBaseLineage, ...]:
    records: list[MaterialBaseLineage] = []
    for group in groups:
        for item in group:
            records.append(item.model_copy(update={"product_index": len(records)}))
    return tuple(records)


def build_denatured_fragments(
    *,
    source_id: str,
    source_top_sequence: str,
    top_cut_boundaries: tuple[int, ...],
    bottom_cut_boundaries: tuple[int, ...],
    top_five_prime_end: EndChemistry,
    top_three_prime_end: EndChemistry,
    bottom_five_prime_end: EndChemistry,
    bottom_three_prime_end: EndChemistry,
) -> tuple[Fragment, ...]:
    """Replay all strand fragments from exact nick boundaries and source end chemistry."""
    length = len(source_top_sequence)
    top_boundaries = (0, *top_cut_boundaries, length)
    bottom_boundaries = (0, *bottom_cut_boundaries, length)
    fragments: list[Fragment] = []
    for start, end in pairwise(top_boundaries):
        fragments.append(
            Fragment(
                fragment_id=f"top-{start}-{end}",
                precursor_strand=Strand.TOP,
                precursor_span=Span(
                    start=Boundary(offset=start),
                    end=Boundary(offset=end),
                ),
                lineage_direction=LineageDirection.FORWARD,
                sequence=source_top_sequence[start:end],
                five_prime_end=(top_five_prime_end if start == 0 else EndChemistry.PHOSPHATE),
                three_prime_end=(top_three_prime_end if end == length else EndChemistry.HYDROXYL),
                lineage=build_lineage(
                    origin_id=source_id,
                    origin_strand=LineageStrand.PRIMARY,
                    origin_indexes=range(start, end),
                ),
            )
        )
    bottom_spans = tuple(pairwise(bottom_boundaries))[::-1]
    for start, end in bottom_spans:
        fragments.append(
            Fragment(
                fragment_id=f"bottom-{start}-{end}",
                precursor_strand=Strand.BOTTOM,
                precursor_span=Span(
                    start=Boundary(offset=start),
                    end=Boundary(offset=end),
                ),
                lineage_direction=LineageDirection.REVERSE,
                sequence=reverse_complement_iupac(source_top_sequence[start:end]),
                five_prime_end=(bottom_five_prime_end if end == length else EndChemistry.PHOSPHATE),
                three_prime_end=(bottom_three_prime_end if start == 0 else EndChemistry.HYDROXYL),
                lineage=build_lineage(
                    origin_id=source_id,
                    origin_strand=LineageStrand.COMPLEMENTARY,
                    origin_indexes=range(end - 1, start - 1, -1),
                ),
            )
        )
    return tuple(fragments)


def observe_pair(
    *,
    left_strand_id: str,
    right_strand_id: str,
    left_index: int,
    right_index: int,
    left_base: str,
    right_base: str,
) -> StrandPairObservation:
    return StrandPairObservation(
        left_strand_id=left_strand_id,
        right_strand_id=right_strand_id,
        left_index=left_index,
        right_index=right_index,
        left_base=left_base,
        right_base=right_base,
        kind=classify_literal_pair(left_base=left_base, right_base=right_base),
    )


def strand_from_sequence(
    *,
    strand_id: str,
    sequence: str,
    five_prime_end: EndChemistry,
    three_prime_end: EndChemistry,
    origin_id: str,
    origin_strand: LineageStrand,
    origin_indexes: Iterable[int],
) -> MolecularStrand:
    return MolecularStrand(
        strand_id=strand_id,
        sequence=sequence,
        five_prime_end=five_prime_end,
        three_prime_end=three_prime_end,
        lineage=build_lineage(
            origin_id=origin_id,
            origin_strand=origin_strand,
            origin_indexes=origin_indexes,
        ),
    )


__all__ = [
    "build_denatured_fragments",
    "build_lineage",
    "observe_pair",
    "reindex_lineage",
    "strand_from_sequence",
]
