"""Matched molecular states and lineage-derived regions for a selected construction."""

from typing import Literal

from hop_design.models.base import HopModel
from hop_design.models.construction.complete.product import MaterializedFinalProduct
from hop_design.models.construction.payload import ConstructionEndpoint


class ProductDiagramBase(HopModel):
    strand_index: Literal[0, 1]
    product_index: int
    column: int
    base: str
    region: Literal["open", "stem", "closing", "unmapped"]


class ProductStageProjection(HopModel):
    hairpin_state_id: str
    hairpin_role: Literal["endpoint", "intermediate"]
    endpoint: ConstructionEndpoint
    product: MaterializedFinalProduct
    bases: tuple[ProductDiagramBase, ...]
    pairing_columns: tuple[int, ...]

    unavailable_reason: str | None = None
