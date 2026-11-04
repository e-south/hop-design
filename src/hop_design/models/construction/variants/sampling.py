"""Replayable teaching choices retain the exact underlying selection contract."""

from typing import Any, Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction.surveys.selection import Digest


class GuidedSampleRequest(HopModel):
    seed: int = Field(ge=0, lt=2**64)
    stage: Literal["hairpin", "endpoint"] = "endpoint"
    history: tuple[str, ...] = ()


class GuidedSampleReceipt(GuidedSampleRequest):
    schema_id: Literal["hop.guided-sample/v1"] = Field(
        default="hop.guided-sample/v1", alias="schema"
    )
    strategy: Literal["families/v1", "loop/v1"] = "families/v1"
    pool_digest: Digest
    eligible_digest: Digest
    query: dict[str, Any]
    selection: dict[str, Any]
    eligible_products: int = Field(ge=1)
    eligible_preparations: int = Field(ge=1)
    family_id: Digest
    product_identity: str
    status: Literal[
        "selected",
        "different_family",
        "different_product",
        "preparation_alternative",
        "only_preparation",
        "loop_alternative",
    ]
    explanation: str
    coordinate_changes: tuple[dict[str, Any], ...] = ()
