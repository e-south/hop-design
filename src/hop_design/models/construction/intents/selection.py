"""An exact hairpin preparation selected from a saved optional-intent discovery."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from ..surveys.query import InterfaceSurveyQuery
from ..variants.query import Digest
from .refinement import DesignRefinementQuery


class HairpinDesignSelection(HopModel):
    schema_id: Literal["hop.hairpin-design-selection/v1", "hop.hairpin-design-selection/v2"] = (
        Field(default="hop.hairpin-design-selection/v1", alias="schema")
    )
    request_digest: Digest
    snapshot_digest: Digest
    query_digest: Digest
    option_label: str = Field(min_length=1)
    materialized_realization_id: str = Field(min_length=1)
    query: InterfaceSurveyQuery | DesignRefinementQuery

    @model_validator(mode="after")
    def versioned_refinement(self) -> "HairpinDesignSelection":
        if isinstance(self.query, DesignRefinementQuery) != (
            self.schema_id == "hop.hairpin-design-selection/v2"
        ):
            raise ValueError("Preserved selections require hop.hairpin-design-selection/v2.")
        return self
