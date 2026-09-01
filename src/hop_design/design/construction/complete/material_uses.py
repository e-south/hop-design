"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/complete/material_uses.py

Assigns contextual route uses to exact complete-construction materials.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete import (
    ExactConstructionMaterial,
    MaterialResolutionMode,
    MaterialRouteEntry,
    MaterialUse,
    MaterialUseRole,
    PcrPrimer,
    SourceDuplexPreparationAuthority,
)


def pcr_material_uses(
    *,
    source_preparation: SourceDuplexPreparationAuthority,
    adapter: ExactConstructionMaterial,
    forward_primer: PcrPrimer,
    reverse_primer: PcrPrimer,
    resolution_modes: tuple[
        MaterialResolutionMode,
        MaterialResolutionMode,
        MaterialResolutionMode,
    ],
) -> tuple[MaterialUse, MaterialUse, MaterialUse, MaterialUse, MaterialUse]:
    """Return ordered route uses for the five PCR material functions."""
    adapter_mode, forward_mode, reverse_mode = resolution_modes
    return (
        source_preparation.prepared_top_use,
        source_preparation.prepared_bottom_use,
        MaterialUse.create(
            material_id=adapter.material_id,
            role=MaterialUseRole.LIGATION_ADAPTER,
            specification_resolution_mode=adapter_mode,
            route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
        ),
        MaterialUse.create(
            material_id=forward_primer.oligo.material_id,
            role=MaterialUseRole.ENDPOINT_FORWARD_PRIMER,
            specification_resolution_mode=forward_mode,
            route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
        ),
        MaterialUse.create(
            material_id=reverse_primer.oligo.material_id,
            role=MaterialUseRole.ENDPOINT_REVERSE_PRIMER,
            specification_resolution_mode=reverse_mode,
            route_entry=MaterialRouteEntry.REQUIRED_EXTERNAL,
        ),
    )


__all__ = ["pcr_material_uses"]
