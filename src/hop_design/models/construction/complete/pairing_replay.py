"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/pairing_replay.py

Derives exact complete-route duplex and foldback pairing authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete.evaluation_inputs import LinearSourceEmbedding
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import (
    Fragment,
    LineageStrand,
    MolecularStrand,
    StrandPairObservation,
)
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


def compose_foldback_pairings(
    duplex: tuple[StrandPairObservation, ...],
    foldback: tuple[StrandPairObservation, ...],
) -> tuple[StrandPairObservation, ...]:
    """Replace source-duplex associations at bases reassigned by foldback annealing."""
    foldback_coordinates = tuple(
        coordinate
        for pair in foldback
        for coordinate in (
            (pair.left_strand_id, pair.left_index),
            (pair.right_strand_id, pair.right_index),
        )
    )
    if len(foldback_coordinates) != len(set(foldback_coordinates)):
        raise ValueError("Foldback annealing pairs must use each strand coordinate once.")
    reassigned = set(foldback_coordinates)
    retained_duplex = tuple(
        pair
        for pair in duplex
        if (pair.left_strand_id, pair.left_index) not in reassigned
        and (pair.right_strand_id, pair.right_index) not in reassigned
    )
    return (*retained_duplex, *foldback)


def _lift_foldback_coordinate(
    strands: tuple[MolecularStrand, ...],
    *,
    fragment: Fragment,
    local_index: int,
    base: str,
    embedding: LinearSourceEmbedding,
    source_id: str,
    complement_id: str,
) -> tuple[str, int]:
    try:
        local_lineage = fragment.lineage[local_index]
        local_base = fragment.sequence[local_index]
    except IndexError as exc:
        raise ValueError("Foldback pairing coordinate must lie within its exact fragment.") from exc
    if local_base != base:
        raise ValueError("Foldback pairing base must replay its exact fragment coordinate.")
    if local_lineage.origin_strand is LineageStrand.PRIMARY:
        origin_id = source_id
        origin_index = embedding.local_reference_offset + local_lineage.origin_index
    else:
        origin_id = complement_id
        origin_index = (
            embedding.local_complement_offset
            + embedding.local_source_length
            - 1
            - local_lineage.origin_index
        )
    matches = tuple(
        (strand, index)
        for strand in strands
        for index, lineage in enumerate(strand.lineage)
        if lineage.origin_id == origin_id
        and lineage.origin_strand is local_lineage.origin_strand
        and lineage.origin_index == origin_index
    )
    if len(matches) != 1:
        raise ValueError(
            "Foldback pairing coordinate must map to one exact selected material base."
        )
    strand, index = matches[0]
    if strand.sequence[index] != base:
        raise ValueError("Lifted foldback pairing base must replay the selected material.")
    return strand.strand_id, index


def lift_foldback_pairings(
    strands: tuple[MolecularStrand, ...],
    *,
    fragments: tuple[Fragment, ...],
    pairings: tuple[StrandPairObservation, ...],
    embedding: LinearSourceEmbedding,
    source_id: str,
    complement_id: str,
) -> tuple[StrandPairObservation, ...]:
    """Lift local foldback associations into exact selected-material coordinates."""
    fragments_by_id = {fragment.fragment_id: fragment for fragment in fragments}
    if len(fragments_by_id) != len(fragments):
        raise ValueError("Foldback fragments must have unique identities.")
    lifted: list[StrandPairObservation] = []
    for pair in pairings:
        try:
            left_fragment = fragments_by_id[pair.left_strand_id]
            right_fragment = fragments_by_id[pair.right_strand_id]
        except KeyError as exc:
            raise ValueError(
                "Foldback pairing must reference exact local fragment authorities."
            ) from exc
        left_strand_id, left_index = _lift_foldback_coordinate(
            strands,
            fragment=left_fragment,
            local_index=pair.left_index,
            base=pair.left_base,
            embedding=embedding,
            source_id=source_id,
            complement_id=complement_id,
        )
        right_strand_id, right_index = _lift_foldback_coordinate(
            strands,
            fragment=right_fragment,
            local_index=pair.right_index,
            base=pair.right_base,
            embedding=embedding,
            source_id=source_id,
            complement_id=complement_id,
        )
        lifted.append(
            pair.model_copy(
                update={
                    "left_strand_id": left_strand_id,
                    "right_strand_id": right_strand_id,
                    "left_index": left_index,
                    "right_index": right_index,
                }
            )
        )
    return tuple(lifted)


def annealed_pairings(
    strands: tuple[MolecularStrand, ...],
    *,
    foldback: FoldbackLocalRealization,
    embedding: LinearSourceEmbedding,
    source_id: str,
    complement_id: str,
    source_length: int,
) -> tuple[StrandPairObservation, ...]:
    """Combine substrate duplex pairs with exact retained foldback-arm pairs."""
    duplex = duplex_pairings(
        strands,
        source_id=source_id,
        complement_id=complement_id,
        source_length=source_length,
    )
    foldback_pairs = lift_foldback_pairings(
        strands,
        fragments=foldback.molecular_fragments,
        pairings=foldback.annealing_pairs,
        embedding=embedding,
        source_id=source_id,
        complement_id=complement_id,
    )
    return compose_foldback_pairings(duplex, foldback_pairs)


__all__ = [
    "annealed_pairings",
    "compose_foldback_pairings",
    "duplex_pairings",
    "lift_foldback_pairings",
]
