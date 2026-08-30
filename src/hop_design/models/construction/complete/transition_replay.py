"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/transition_replay.py

Replays exact non-enzyme molecular transformations in complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from collections import Counter

from hop_design.models.molecular_state import (
    EndChemistry,
    MaterialBaseLineage,
    MolecularStrand,
    StrandPairObservation,
)
from hop_design.models.physical import classify_literal_pair

from .state import ConstructionState


def _strand_signature(strand: MolecularStrand) -> str:
    return json.dumps(
        strand.model_dump(mode="json", exclude={"strand_id"}),
        sort_keys=True,
        separators=(",", ":"),
    )


def _validate_pairings(state: ConstructionState) -> None:
    observed = set()
    for pair in state.pairings:
        key = (
            pair.left_strand_id,
            pair.left_index,
            pair.right_strand_id,
            pair.right_index,
        )
        if key in observed or pair.kind is not classify_literal_pair(
            left_base=pair.left_base,
            right_base=pair.right_base,
        ):
            raise ValueError("Annealing must record unique literal base-pair associations.")
        observed.add(key)


def _reindexed_lineage(strands: tuple[MolecularStrand, ...]) -> tuple[MaterialBaseLineage, ...]:
    return tuple(
        item.model_copy(update={"product_index": index})
        for index, item in enumerate(item for strand in strands for item in strand.lineage)
    )


def _pairing_signature(pair: StrandPairObservation) -> tuple[object, ...]:
    return (
        pair.left_strand_id,
        pair.left_index,
        pair.right_strand_id,
        pair.right_index,
        pair.left_base,
        pair.right_base,
        pair.kind,
    )


def validate_non_enzyme_transition(
    *,
    kind: str,
    pre_state: ConstructionState,
    post_state: ConstructionState,
) -> None:
    """Require each declared transition kind to replay exact molecular facts."""
    if kind == "denaturation":
        if (
            Counter(map(_strand_signature, pre_state.molecules))
            != Counter(map(_strand_signature, post_state.molecules))
            or post_state.formed_bonds != pre_state.formed_bonds
        ):
            raise ValueError("Denaturation must preserve exact strands, chemistry, and lineage.")
        if not pre_state.pairings or post_state.pairings:
            raise ValueError("Denaturation must remove the exact duplex associations.")
        return
    if kind == "fragment_selection":
        if any(strand not in pre_state.molecules for strand in post_state.molecules):
            raise ValueError("Fragment selection may retain only exact precursor strands.")
        if post_state.pairings or post_state.formed_bonds:
            raise ValueError("Fragment selection cannot create pairings or covalent bonds.")
        return
    if kind == "annealing":
        if pre_state.molecules != post_state.molecules:
            raise ValueError(
                "Annealing must preserve exact strand sequence, chemistry, and lineage."
            )
        if pre_state.pairings or not post_state.pairings or post_state.formed_bonds:
            raise ValueError("Annealing must add only explicit noncovalent base associations.")
        _validate_pairings(post_state)
        return
    if kind == "ligation":
        if len(post_state.molecules) != 1 or len(post_state.formed_bonds) != 1:
            raise ValueError("Ligation must create one exact covalently joined product strand.")
        bond_state = post_state.formed_bonds[0]
        strands = {item.strand_id: item for item in pre_state.molecules}
        try:
            upstream = strands[bond_state.bond.upstream_strand_id]
            downstream = strands[bond_state.bond.downstream_strand_id]
        except KeyError as exc:
            raise ValueError("Ligation bond must reference exact precursor strands.") from exc
        product = post_state.molecules[0]
        if (
            upstream.three_prime_end is not EndChemistry.HYDROXYL
            or downstream.five_prime_end is not EndChemistry.PHOSPHATE
        ):
            raise ValueError("Ligation requires an upstream hydroxyl and downstream phosphate.")
        if (
            bond_state.product_strand_id != product.strand_id
            or product.sequence != upstream.sequence + downstream.sequence
            or product.five_prime_end is not upstream.five_prime_end
            or product.three_prime_end is not downstream.three_prime_end
            or product.lineage != _reindexed_lineage((upstream, downstream))
        ):
            raise ValueError("Ligation product must replay exact precursor sequence and lineage.")
        _validate_pairings(post_state)
        precursor_lineage = {
            (strand.strand_id, index): (
                lineage.origin_id,
                lineage.origin_strand,
                lineage.origin_index,
            )
            for strand in pre_state.molecules
            for index, lineage in enumerate(strand.lineage)
        }
        product_indexes = {
            (lineage.origin_id, lineage.origin_strand, lineage.origin_index): index
            for index, lineage in enumerate(product.lineage)
        }
        expected_pairings = {
            (
                product.strand_id,
                product_indexes[precursor_lineage[(pair.left_strand_id, pair.left_index)]],
                product.strand_id,
                product_indexes[precursor_lineage[(pair.right_strand_id, pair.right_index)]],
                pair.left_base,
                pair.right_base,
                pair.kind,
            )
            for pair in pre_state.pairings
        }
        if {_pairing_signature(pair) for pair in post_state.pairings} != expected_pairings:
            raise ValueError("Ligation must preserve exact annealed base-pair associations.")
        return
    if kind == "primer_extension":
        raise ValueError("Primer extension requires an explicit template-copying authority.")


__all__ = ["validate_non_enzyme_transition"]
