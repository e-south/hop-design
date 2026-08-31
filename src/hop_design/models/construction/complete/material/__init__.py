"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/__init__.py

Exposes exact route-material contracts for complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .identity import construction_material_id
from .production import ProducedMaterialBinding
from .spec import (
    ExactConstructionMaterial,
    MaterialResolutionMode,
    PcrPrimer,
)
from .use import MaterialRouteEntry, MaterialUse, MaterialUseRole

__all__ = [
    "ExactConstructionMaterial",
    "MaterialResolutionMode",
    "MaterialRouteEntry",
    "MaterialUse",
    "MaterialUseRole",
    "PcrPrimer",
    "ProducedMaterialBinding",
    "construction_material_id",
]
