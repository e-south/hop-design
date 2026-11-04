"""Derived search addresses are hints, never imported construction witnesses."""

from dataclasses import dataclass

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.materials import external_material_uses


class PreferenceOutOfScope(ValueError):
    """A reference has no exact candidate inside the declared molecular envelope."""


@dataclass(frozen=True, order=True)
class MaterialSignature:
    role: str
    sequence_5prime: str
    five_prime_end: str
    three_prime_end: str


def material_signature(
    preparation: MaterializedConstructionRealization,
) -> tuple[MaterialSignature, ...]:
    """Compare external orders by role and chemistry, independently of route IDs."""
    return tuple(
        sorted(
            MaterialSignature(
                use.role.value,
                material.sequence_5prime,
                material.five_prime_end.value,
                material.three_prime_end.value,
            )
            for material, use in external_material_uses(preparation)
        )
    )


@dataclass(frozen=True, order=True)
class PreparationAddress:
    target: int
    geometry_rank: int
    page: int
    context_rank: int
    source_context: str
    materials: tuple[MaterialSignature, ...]
