"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/lineage.py

Maps complete-route molecular strands to exact caller material coordinates.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete.materials import (
    MaterialOccurrence,
    foldback_occurrences,
    whole_source_occurrences,
)
from hop_design.models.construction.complete.route_lineage import (
    material_strand,
    reaction_molecule_strands,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import CovalentBond, MolecularStrand


def final_hairpin_strand(
    *,
    foldback: FoldbackLocalRealization,
    prefix: str,
    return_arm: str,
    selected_strands: tuple[MolecularStrand, ...],
    ligation_bond: CovalentBond,
) -> MolecularStrand:
    """Ligate the exact selected source fragments without reconstructing lineage."""
    upstream = next(
        strand
        for strand in selected_strands
        if strand.strand_id == ligation_bond.upstream_strand_id
    )
    downstream = next(
        strand
        for strand in selected_strands
        if strand.strand_id == ligation_bond.downstream_strand_id
    )
    expected = prefix + foldback.retained_sequence + return_arm
    if upstream.sequence + downstream.sequence != expected:
        raise ValueError("Selected fragments must concatenate to the exact hairpin product.")
    lineage = tuple(
        item.model_copy(update={"product_index": index})
        for index, item in enumerate((*upstream.lineage, *downstream.lineage))
    )
    return MolecularStrand(
        strand_id="complete-ssdna-hairpin",
        sequence=expected,
        five_prime_end=upstream.five_prime_end,
        three_prime_end=downstream.three_prime_end,
        lineage=lineage,
    )


__all__ = [
    "MaterialOccurrence",
    "final_hairpin_strand",
    "foldback_occurrences",
    "material_strand",
    "reaction_molecule_strands",
    "whole_source_occurrences",
]
