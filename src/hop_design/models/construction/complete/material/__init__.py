"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/__init__.py

Exposes exact route-material contracts for complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from .spec import (
    ExactConstructionMaterial,
    LinearSourceMaterializationSpec,
    MaterialOrigin,
    PcrPrimer,
)

__all__ = [
    "ExactConstructionMaterial",
    "LinearSourceMaterializationSpec",
    "MaterialOrigin",
    "PcrPrimer",
]
