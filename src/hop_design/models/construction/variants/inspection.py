"""Inspection names a preparation and state, never a replacement design query."""

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel

from .query import Digest


class MolecularAddress(HopModel):
    state_id: str = Field(min_length=1, max_length=200)
    strand_id: str = Field(min_length=1, max_length=200)
    index: int = Field(ge=0)


class ScaffoldInspectionRequest(HopModel):
    schema_id: Literal["hop.scaffold-inspection-request/v1"] = Field(
        default="hop.scaffold-inspection-request/v1", alias="schema"
    )
    result_digest: Digest
    query_digest: Digest
    option_label: str = Field(min_length=1, max_length=200)
    state: str = Field(min_length=1, max_length=200)
    focus: MolecularAddress | None = None
