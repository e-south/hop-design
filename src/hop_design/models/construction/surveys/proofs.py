"""Replayable complete-local exclusion, distinct from whole-route infeasibility."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.request import LocalNeighborhoodRequest

from .execution import SurveyEvaluationLimits


class EmptyBasalFacts(HopModel):
    scope: Literal["local_molecular_admission"] = "local_molecular_admission"
    completion: Literal["complete"] = "complete"
    candidate_count: int = Field(ge=0)
    program_count: int = Field(ge=0)
    admitted_configurations: Literal[0] = 0


class EmptyBasalPlane(HopModel):
    schema_name: Literal["hop.empty-basal-plane/v1"] = Field(
        default="hop.empty-basal-plane/v1", alias="schema"
    )
    survey_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    producer_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target: int = Field(ge=0)
    branch: int = Field(ge=0)
    coordinates: tuple[int, int, int, int, int]
    free_axes: tuple[Literal["foldback_case"], Literal["source_context"]] = (
        "foldback_case",
        "source_context",
    )
    basal_request: LocalNeighborhoodRequest
    evaluation_limits: SurveyEvaluationLimits
    facts: EmptyBasalFacts

    @model_validator(mode="after")
    def complete_domain(self) -> "EmptyBasalPlane":
        if (
            self.basal_request.family.value != "basal"
            or self.basal_request.search.sequence_partition is not None
            or any(c < 0 for c in self.coordinates)
        ):
            raise ValueError("A plane proof requires the entire unpartitioned basal domain.")
        return self
