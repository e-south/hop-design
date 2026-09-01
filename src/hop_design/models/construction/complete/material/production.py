"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/production.py

Binds exact produced route materials to their molecular-state strands.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.molecular_state import MaterialBaseLineage

from .spec import ExactConstructionMaterial
from .use import MaterialRouteEntry, MaterialUse


class ProducedMaterialBinding(HopModel):
    """One exact material produced as a strand in a sealed molecular state."""

    material: ExactConstructionMaterial
    material_use: MaterialUse
    product_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    product_strand_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
    upstream_lineage: tuple[MaterialBaseLineage, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_binding(self) -> ProducedMaterialBinding:
        if self.material_use.material_id != self.material.material_id:
            raise ValueError("Produced material use must bind its exact molecular material.")
        if self.material_use.route_entry is not MaterialRouteEntry.MODELED_PRODUCT:
            raise ValueError("Produced material use must enter the route as a modeled product.")
        if len(self.upstream_lineage) != len(self.material.sequence_5prime) or tuple(
            item.product_index for item in self.upstream_lineage
        ) != tuple(range(len(self.material.sequence_5prime))):
            raise ValueError("Produced material binding must preserve complete upstream lineage.")
        return self


__all__ = ["ProducedMaterialBinding"]
