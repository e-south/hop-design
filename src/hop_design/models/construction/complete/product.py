"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/product.py

Defines the exact endpoint molecular product and design-sequence projection.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.realization import FinalProductReference
from hop_design.models.molecular_state import MolecularStrand, SequenceProjection


class MaterializedFinalProduct(HopModel):
    """Exact endpoint product with the encoding projection used for design comparison."""

    reference: FinalProductReference
    strands: tuple[MolecularStrand, ...] = Field(min_length=1)
    encoding_projection: SequenceProjection

    @model_validator(mode="after")
    def validate_product(self) -> MaterializedFinalProduct:
        if self.reference.topology == "single_stranded_hairpin" and len(self.strands) != 1:
            raise ValueError("A single-strand endpoint must contain exactly one exact strand.")
        if self.reference.sequence != self.strands[0].sequence:
            raise ValueError("Final-product reference must equal its primary exact strand.")
        return self


__all__ = ["MaterializedFinalProduct"]
