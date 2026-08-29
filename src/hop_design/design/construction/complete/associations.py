"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/associations.py

Derives exact duplex and hairpin pairing evidence from source-material lineage.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete.pairing_replay import (
    annealed_pairings,
    duplex_pairings,
)
from hop_design.models.molecular_state import MolecularStrand, StrandPairObservation


def product_pairings(
    pairings: tuple[StrandPairObservation, ...],
    *,
    precursor_strands: tuple[MolecularStrand, ...],
    product: MolecularStrand,
) -> tuple[StrandPairObservation, ...]:
    """Remap precursor pairing endpoints onto their exact ligated-product bases."""
    precursor = {
        (strand.strand_id, index): (item.origin_id, item.origin_index)
        for strand in precursor_strands
        for index, item in enumerate(strand.lineage)
    }
    product_indexes = {
        (item.origin_id, item.origin_index): index for index, item in enumerate(product.lineage)
    }
    records: list[StrandPairObservation] = []
    for pair in pairings:
        left_index = product_indexes[precursor[(pair.left_strand_id, pair.left_index)]]
        right_index = product_indexes[precursor[(pair.right_strand_id, pair.right_index)]]
        records.append(
            pair.model_copy(
                update={
                    "left_strand_id": product.strand_id,
                    "right_strand_id": product.strand_id,
                    "left_index": left_index,
                    "right_index": right_index,
                }
            )
        )
    return tuple(records)


__all__ = ["annealed_pairings", "duplex_pairings", "product_pairings"]
