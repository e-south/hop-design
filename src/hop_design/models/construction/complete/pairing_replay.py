"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pairing_replay.py

Derives exact complete-route duplex and foldback pairing authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import MolecularStrand, StrandPairObservation
from hop_design.models.physical import classify_literal_pair


def duplex_pairings(
    strands: tuple[MolecularStrand, ...],
    *,
    source_id: str,
    complement_id: str,
    source_length: int,
) -> tuple[StrandPairObservation, ...]:
    """Pair source and complementary bases by exact material coordinates."""
    source_bases: dict[int, tuple[MolecularStrand, int]] = {}
    complement_bases: dict[int, tuple[MolecularStrand, int]] = {}
    for strand in strands:
        for index, item in enumerate(strand.lineage):
            if item.origin_id == source_id:
                source_bases[item.origin_index] = (strand, index)
            elif item.origin_id == complement_id:
                complement_bases[item.origin_index] = (strand, index)
    pairs: list[StrandPairObservation] = []
    for source_index, (left, left_index) in sorted(source_bases.items()):
        paired = complement_bases.get(source_length - 1 - source_index)
        if paired is None:
            continue
        right, right_index = paired
        left_base = left.sequence[left_index]
        right_base = right.sequence[right_index]
        pairs.append(
            StrandPairObservation(
                left_strand_id=left.strand_id,
                right_strand_id=right.strand_id,
                left_index=left_index,
                right_index=right_index,
                left_base=left_base,
                right_base=right_base,
                kind=classify_literal_pair(left_base=left_base, right_base=right_base),
            )
        )
    return tuple(pairs)


def annealed_pairings(
    strands: tuple[MolecularStrand, ...],
    *,
    foldback: FoldbackLocalRealization,
    source_id: str,
    complement_id: str,
    source_length: int,
) -> tuple[StrandPairObservation, ...]:
    """Combine substrate duplex pairs with exact retained foldback-arm pairs."""
    pairs = list(
        duplex_pairings(
            strands,
            source_id=source_id,
            complement_id=complement_id,
            source_length=source_length,
        )
    )
    bottom_id = foldback.annealing_pairs[0].left_strand_id
    bottom = next(strand for strand in strands if f"-{bottom_id}-" in strand.strand_id)
    pairs.extend(
        item.model_copy(
            update={
                "left_strand_id": bottom.strand_id,
                "right_strand_id": bottom.strand_id,
            }
        )
        for item in foldback.annealing_pairs
    )
    return tuple(pairs)


__all__ = ["annealed_pairings", "duplex_pairings"]
