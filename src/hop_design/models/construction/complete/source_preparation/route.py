"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_preparation/route.py

Defines linear-source preparation and endpoint auxiliary material inputs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.base import HopModel

from ..material import ExactConstructionMaterial, PcrPrimer
from .policy import SourceDuplexPreparationPolicy


class LinearSourceMaterializationSpec(HopModel):
    """Source preparation plus exact endpoint-dependent auxiliary oligos."""

    source_preparation: SourceDuplexPreparationPolicy
    adapter: ExactConstructionMaterial | None = None
    hairpin_pcr_forward_primer: PcrPrimer | None = None
    hairpin_pcr_reverse_primer: PcrPrimer | None = None


__all__ = ["LinearSourceMaterializationSpec"]
