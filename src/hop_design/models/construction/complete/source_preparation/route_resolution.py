"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/route_resolution.py

Resolves one complete-route source preparation against exact foldback obligations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Collection

from hop_design.models.construction.foldback import FoldbackMaterialRequirement
from hop_design.models.coordinates import Span
from hop_design.models.molecular_state import EndChemistry

from .authority import SourceDuplexPreparationAuthority
from .policy import SourceDuplexPreparationPolicy
from .resolution import SourcePreparationResolutionError, resolve_source_duplex_preparation


def resolve_route_source_preparation(
    *,
    policy: SourceDuplexPreparationPolicy,
    source_sequence: str,
    expected_complement_sequence: str,
    payload_source_span: Span,
    material_requirements: Collection[FoldbackMaterialRequirement],
) -> SourceDuplexPreparationAuthority:
    """Resolve and verify the copied duplex required by one complete route."""
    preparation = resolve_source_duplex_preparation(
        policy=policy,
        source_sequence=source_sequence,
        payload_source_span=payload_source_span,
        reference_five_prime_end=(
            EndChemistry.PHOSPHATE
            if FoldbackMaterialRequirement.SOURCE_TOP_5PRIME_PHOSPHATE in material_requirements
            else EndChemistry.HYDROXYL
        ),
        complement_five_prime_end=(
            EndChemistry.PHOSPHATE
            if FoldbackMaterialRequirement.SOURCE_BOTTOM_5PRIME_PHOSPHATE in material_requirements
            else EndChemistry.HYDROXYL
        ),
    )
    source, complement = tuple(
        binding.material for binding in preparation.produced_material_bindings
    )
    if (
        source.sequence_5prime != source_sequence
        or complement.sequence_5prime != expected_complement_sequence
    ):
        raise SourcePreparationResolutionError(
            "Source preparation must produce the exact complete-route duplex."
        )
    return preparation


__all__ = ["resolve_route_source_preparation"]
