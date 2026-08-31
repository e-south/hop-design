"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/__init__.py

Exposes exact route-material contracts for complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .production import ProducedMaterialBinding
from .spec import (
    ExactConstructionMaterial,
    LinearSourceMaterializationSpec,
    MaterialOrigin,
    MaterialResolutionMode,
    PcrPrimer,
)

__all__ = [
    "ExactConstructionMaterial",
    "LinearSourceMaterializationSpec",
    "MaterialOrigin",
    "MaterialResolutionMode",
    "PcrPrimer",
    "ProducedMaterialBinding",
]
