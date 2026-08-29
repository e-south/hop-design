"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/associations.py

Defines exact molecular association and ligation evidence in route states.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.molecular_state import CovalentBond


class ConstructionBondState(HopModel):
    """One exact precursor ligation bond and the product strand it creates."""

    bond: CovalentBond
    product_strand_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_product(self) -> ConstructionBondState:
        if self.product_strand_id in {
            self.bond.upstream_strand_id,
            self.bond.downstream_strand_id,
        }:
            raise ValueError("A ligation product must be distinct from both precursor strands.")
        return self


__all__ = ["ConstructionBondState"]
