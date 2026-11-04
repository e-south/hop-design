"""Required membership within an admitted conditional pool, without new search permissions."""

from typing import Literal

from pydantic import Field

from hop_design.models.construction.comparisons.request import (
    ComparisonRequirements as ComparisonRequirements,
)

from .query import Digest


class VariantComparisonRequest(ComparisonRequirements):
    schema_id: Literal["hop.variant-comparison-request/v1"] = Field(
        default="hop.variant-comparison-request/v1", alias="schema"
    )
    result_digest: Digest
    query_digest: Digest
