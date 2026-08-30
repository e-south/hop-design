"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/lineage.py

Maps complete-route molecular strands to exact caller material coordinates.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete import ExactConstructionMaterial
from hop_design.models.construction.complete.route_lineage import (
    MaterialOccurrence,
    foldback_occurrences,
    material_strand,
    reaction_molecule_strands,
    whole_source_occurrences,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.molecular_state import MolecularStrand


def final_hairpin_strand(
    *,
    foldback: FoldbackLocalRealization,
    prefix: str,
    return_arm: str,
    source: ExactConstructionMaterial,
    source_complement: ExactConstructionMaterial,
    selected_strands: tuple[MolecularStrand, ...],
) -> MolecularStrand:
    """Ligate the exact selected source fragments without reconstructing lineage."""
    top = next(
        strand
        for strand in selected_strands
        if all(item.origin_id == source.material_id for item in strand.lineage)
    )
    bottom = next(
        strand
        for strand in selected_strands
        if all(item.origin_id == source_complement.material_id for item in strand.lineage)
    )
    expected = prefix + foldback.retained_sequence + return_arm
    if top.sequence + bottom.sequence != expected:
        raise ValueError("Selected fragments must concatenate to the exact hairpin product.")
    lineage = tuple(
        item.model_copy(update={"product_index": index})
        for index, item in enumerate((*top.lineage, *bottom.lineage))
    )
    return MolecularStrand(
        strand_id="complete-ssdna-hairpin",
        sequence=expected,
        five_prime_end=top.five_prime_end,
        three_prime_end=bottom.three_prime_end,
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
