"""One preparation-wide inspection; viewing never changes the design query."""

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel

from .inspection import MolecularAddress
from .query import Digest


class ScaffoldAtlasRequest(HopModel):
    schema_id: Literal["hop.scaffold-atlas-request/v1"] = Field(
        default="hop.scaffold-atlas-request/v1", alias="schema"
    )
    result_digest: Digest
    query_digest: Digest
    option_label: str = Field(min_length=1, max_length=200)
    focus: MolecularAddress | None = None
