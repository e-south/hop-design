"""Public comparative intent and its exact, portable selected membership."""

from typing import Literal, Self

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from ..comparisons.request import ComparisonAssessment
from ..surveys.query import InterfaceSurveyQuery
from ..surveys.selection import InterfaceSurveySelection
from ..variants.query import Digest, MolecularStage
from .insert_selection import InsertDesignSelection
from .refinement import DesignRefinementQuery
from .selection import HairpinDesignSelection


class DesignComparisonRequest(ComparisonAssessment):
    schema_id: Literal["hop.design-comparison-request/v1"] = Field(
        default="hop.design-comparison-request/v1", alias="schema"
    )
    stage: MolecularStage


class DesignSetSelectionBase[Selection](HopModel):
    request_digest: Digest
    snapshot_digest: Digest
    query_digest: Digest
    comparison_digest: Digest
    request: DesignComparisonRequest
    query: InterfaceSurveyQuery | DesignRefinementQuery
    set_label: str = Field(min_length=1)
    set_id: Digest
    baseline: str = Field(min_length=1)
    members: dict[str, Selection] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def declared_baseline(self) -> Self:
        if self.baseline not in self.members:
            raise ValueError("The baseline must name a selected comparison member.")
        return self


class DesignSetSelection(DesignSetSelectionBase[HairpinDesignSelection]):
    schema_id: Literal["hop.design-set-selection/v1"] = Field(
        default="hop.design-set-selection/v1", alias="schema"
    )


class InsertDesignSetSelection(
    DesignSetSelectionBase[InterfaceSurveySelection | InsertDesignSelection]
):
    schema_id: Literal["hop.design-set-selection/v2"] = Field(
        default="hop.design-set-selection/v2", alias="schema"
    )
    selection_digest: Digest
