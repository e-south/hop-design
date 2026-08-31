"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/production.py

Binds exact produced route materials to their molecular-state strands.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field

from hop_design.models.base import HopModel

from .spec import ExactConstructionMaterial


class ProducedMaterialBinding(HopModel):
    """One exact material produced as a strand in a sealed molecular state."""

    material: ExactConstructionMaterial
    product_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    product_strand_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")


__all__ = ["ProducedMaterialBinding"]
