"""Shared sequence and regional correspondence facts for screen and print."""

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel

from ..complete.product import MaterializedFinalProduct
from .hairpin import HairpinPortraitProjection
from .sequence_difference import SequenceRegionDifference


class FoldedSequenceView(HopModel):
    schema_id: Literal["hop.folded-sequence-view/v1"] = Field(
        default="hop.folded-sequence-view/v1", alias="schema"
    )
    label: str
    reference_label: str
    portrait: HairpinPortraitProjection
    regions: tuple[SequenceRegionDifference, ...]
    changed_material_roles: tuple[str, ...]
    unchanged_material_roles: tuple[str, ...]
    pairing_relationships_unchanged: bool
    endpoint_product: MaterializedFinalProduct
    endpoint_sequence_differences: tuple[SequenceRegionDifference, ...]
