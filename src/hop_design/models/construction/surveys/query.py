"""Read-only predicates over indexed complete constructions."""

from typing import Literal

from pydantic import Field, model_validator

from ..variants.membership import PreparationQuery
from ..variants.parameters import ParameterSelection, validate_selections


class InterfaceSurveyQuery(PreparationQuery):
    schema_id: Literal["hop.interface-survey-query/v1"] = Field(
        default="hop.interface-survey-query/v1", alias="schema"
    )
    parameters: tuple[ParameterSelection, ...] = Field(default=(), max_length=128)

    @model_validator(mode="after")
    def unique_parameters(self) -> "InterfaceSurveyQuery":
        validate_selections(self.parameters)
        return self
