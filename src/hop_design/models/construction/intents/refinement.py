"""Stage-specific preservation bound to an exact admitted molecular reference."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from ..variants.membership import PreparationQuery
from ..variants.parameters import ParameterSelection, validate_selections
from ..variants.query import Digest, PreservedSurroundings


class DesignReference(HopModel):
    request_digest: Digest
    snapshot_digest: Digest
    materialized_realization_id: str = Field(min_length=1)


class DesignRefinementQuery(PreparationQuery):
    schema_id: Literal["hop.design-refinement/v1"] = Field(
        default="hop.design-refinement/v1", alias="schema"
    )
    reference: DesignReference
    surroundings: PreservedSurroundings
    parameters: tuple[ParameterSelection, ...] = Field(default=(), max_length=128)

    @model_validator(mode="after")
    def unique_parameters(self) -> "DesignRefinementQuery":
        validate_selections(self.parameters)
        return self
