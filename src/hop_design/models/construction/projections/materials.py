"""Read external material identities and their full role membership."""

from hop_design.models.construction.complete.material import (
    ExactConstructionMaterial,
    MaterialRouteEntry,
    MaterialUse,
)
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization


def external_material_uses(
    realization: MaterializedConstructionRealization,
) -> tuple[tuple[ExactConstructionMaterial, MaterialUse], ...]:
    """Read external material uses in preparation and route order."""
    preparation = realization.source_preparation
    entries = (
        (preparation.source_ssdna, preparation.source_ssdna_use),
        (preparation.forward_primer.oligo, preparation.forward_primer_use),
        (preparation.reverse_primer.oligo, preparation.reverse_primer_use),
        *zip(realization.materials, realization.material_uses, strict=True),
    )
    return tuple(
        (material, use)
        for material, use in entries
        if use.route_entry is MaterialRouteEntry.REQUIRED_EXTERNAL
    )


def external_oligos(
    realization: MaterializedConstructionRealization,
) -> tuple[tuple[ExactConstructionMaterial, tuple[MaterialUse, ...]], ...]:
    """Group external uses by molecular identity, preserving first-use order."""
    materials: dict[str, ExactConstructionMaterial] = {}
    uses: dict[str, list[MaterialUse]] = {}
    for material, use in external_material_uses(realization):
        materials[material.material_id] = material
        uses.setdefault(material.material_id, []).append(use)
    return tuple((material, tuple(uses[key])) for key, material in materials.items())
