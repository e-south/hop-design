"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/materials.py

Validates complete-route source states against exact material authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.molecular_state import LineageStrand
from hop_design.models.physical import classify_literal_pair

from .request import (
    ConstructionDiscoveryRequest,
    ExactConstructionMaterial,
    derived_source_material_id,
)
from .state import ConstructionState, ConstructionStatePhase


def derive_source_materials(
    request: ConstructionDiscoveryRequest,
    sequence: str,
    complement_sequence: str,
) -> tuple[ExactConstructionMaterial, ExactConstructionMaterial]:
    """Derive the exact source pair from one request's materialization policy."""
    policy = request.materialization
    return (
        ExactConstructionMaterial(
            material_id=derived_source_material_id(sequence, complementary=False),
            origin=policy.source_origin,
            sequence_5prime=sequence,
            five_prime_end=policy.source_five_prime_end,
            three_prime_end=policy.source_three_prime_end,
        ),
        ExactConstructionMaterial(
            material_id=derived_source_material_id(complement_sequence, complementary=True),
            origin=policy.source_complement_origin,
            sequence_5prime=complement_sequence,
            five_prime_end=policy.source_complement_five_prime_end,
            three_prime_end=policy.source_complement_three_prime_end,
        ),
    )


def validate_initial_material_state(
    state: ConstructionState,
    materials: tuple[ExactConstructionMaterial, ...],
) -> None:
    """Require the first route state to replay both exact source materials."""
    if len(materials) < 2 or len(state.molecules) != 2:
        raise ValueError("Construction source state requires two exact source strands.")
    if state.phase is not ConstructionStatePhase.DUPLEX or not state.pairings:
        raise ValueError("Construction source state must preserve exact duplex association.")
    expected = (
        (materials[0], LineageStrand.PRIMARY),
        (materials[1], LineageStrand.COMPLEMENTARY),
    )
    for strand, (material, lineage_strand) in zip(state.molecules, expected, strict=True):
        if (
            strand.sequence != material.sequence_5prime
            or strand.five_prime_end is not material.five_prime_end
            or strand.three_prime_end is not material.three_prime_end
        ):
            raise ValueError("Construction source state must replay exact material chemistry.")
        if tuple(
            (item.origin_id, item.origin_strand, item.origin_index) for item in strand.lineage
        ) != tuple(
            (material.material_id, lineage_strand, index)
            for index in range(len(material.sequence_5prime))
        ):
            raise ValueError("Construction source state must replay exact material lineage.")
    source_strand, complement_strand = state.molecules
    expected_pairs = {
        (
            source_strand.strand_id,
            index,
            complement_strand.strand_id,
            len(source_strand.sequence) - 1 - index,
            source_strand.sequence[index],
            complement_strand.sequence[len(source_strand.sequence) - 1 - index],
            classify_literal_pair(
                left_base=source_strand.sequence[index],
                right_base=complement_strand.sequence[len(source_strand.sequence) - 1 - index],
            ),
        )
        for index in range(len(source_strand.sequence))
    }
    observed_pairs = {
        (
            item.left_strand_id,
            item.left_index,
            item.right_strand_id,
            item.right_index,
            item.left_base,
            item.right_base,
            item.kind,
        )
        for item in state.pairings
    }
    if observed_pairs != expected_pairs:
        raise ValueError("Construction source state requires complete complement pairing.")


__all__ = ["derive_source_materials", "validate_initial_material_state"]
