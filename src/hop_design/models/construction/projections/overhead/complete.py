"""Stage-specific retained DNA and exact external oligo orders for one preparation."""

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.molecular_state import EndChemistry


class AddedRegion(HopModel):
    strand: str
    strand_id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    region: str
    fate: str


class OligoOrder(HopModel):
    material_id: str
    length_nt: int = Field(gt=0)
    roles: tuple[str, ...]
    five_prime_end: EndChemistry
    three_prime_end: EndChemistry
    modifications: tuple[str, ...]


class ConstructionCost(HopModel):
    materialized_realization_id: str
    endpoint: str
    state_id: str
    stem_arm: str
    added_nt_by_strand: dict[str, int]
    added_regions: tuple[AddedRegion, ...]
    distinct_orders: int = Field(gt=0)
    material_roles: int = Field(gt=0)
    ordered_nt: int = Field(gt=0)
    orders: tuple[OligoOrder, ...]
    achieved_ends: dict[str, dict[str, str]]
    summary_lines: tuple[str, ...]
