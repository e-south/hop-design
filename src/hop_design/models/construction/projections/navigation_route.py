"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/navigation_route.py

Defines additive browse facts for one accepted complete construction route.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget


class ConstructionNavigationAcceptedRoute(HopModel):
    """Navigation facts that are not already present in the complete summary."""

    materialized_realization_id: str = Field(
        pattern=r"^hop:materialized-construction/[0-9a-f]{64}@1$"
    )
    foldback_geometry: FoldbackTarget
    basal_geometry: BasalTarget | None = None
    foldback_relaxation_radius: int = Field(ge=0)
    basal_relaxation_radius: int | None = Field(default=None, ge=0)
    exact_geometry: bool
    cleavage_enzyme_ids: tuple[str, ...]
    retained_non_payload_nt: int = Field(ge=0)
    final_product_topology: Literal["single_stranded_hairpin", "linear_duplex"]

    @model_validator(mode="after")
    def validate_navigation_facts(self) -> ConstructionNavigationAcceptedRoute:
        if (self.basal_geometry is None) != (self.basal_relaxation_radius is None):
            raise ValueError("Basal geometry and relaxation radius must co-occur.")
        radii = (
            self.foldback_relaxation_radius,
            *((cast(int, self.basal_relaxation_radius),) if self.basal_geometry else ()),
        )
        if self.exact_geometry != all(radius == 0 for radius in radii):
            raise ValueError("exact_geometry must derive from every local relaxation radius.")
        if self.cleavage_enzyme_ids != tuple(sorted(set(self.cleavage_enzyme_ids))):
            raise ValueError("Cleavage enzyme ids must be sorted and unique.")
        return self


__all__ = ["ConstructionNavigationAcceptedRoute"]
