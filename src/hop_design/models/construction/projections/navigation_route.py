"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/navigation_route.py

Defines additive browse facts for one accepted complete construction route.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

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
    foldback_retained_overhead_nt: int = Field(ge=0)
    basal_retained_overhead_nt: int | None = Field(default=None, ge=0)
    cleavage_enzyme_ids: tuple[str, ...]
    retained_non_payload_nt: int = Field(ge=0)
    final_product_topology: Literal["single_stranded_hairpin", "linear_duplex"]

    @model_validator(mode="after")
    def validate_navigation_facts(self) -> ConstructionNavigationAcceptedRoute:
        if (self.basal_geometry is None) != (self.basal_retained_overhead_nt is None):
            raise ValueError("Basal geometry and retained overhead must co-occur.")
        if self.cleavage_enzyme_ids != tuple(sorted(set(self.cleavage_enzyme_ids))):
            raise ValueError("Cleavage enzyme ids must be sorted and unique.")
        return self


__all__ = ["ConstructionNavigationAcceptedRoute"]
