"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/material/inventory.py

Derives exact externally required molecular materials from complete route results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .spec import ExactConstructionMaterial

if TYPE_CHECKING:
    from ..realization import MaterializedConstructionRealization


def required_external_materials(
    realization: MaterializedConstructionRealization,
) -> tuple[ExactConstructionMaterial, ...]:
    """Return every exact material that enters the modeled route from outside HOP."""
    preparation = realization.source_preparation
    return (
        preparation.source_ssdna,
        preparation.forward_primer.oligo,
        preparation.reverse_primer.oligo,
        *realization.materials[2:],
    )


__all__ = ["required_external_materials"]
