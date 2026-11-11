"""Exact package pairs approved for unchanged interface-survey computation."""

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel


class SurveyCompatibilityDeclaration(HopModel):
    source_version: str = Field(min_length=1, max_length=100)
    source_content: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_version: str = Field(min_length=1, max_length=100)
    target_code: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    computation_contract: Literal["interface-survey/1"]


class SurveyCompatibilityPolicy(HopModel):
    schema_id: Literal["hop.survey-compatibility/v1"] = Field(alias="schema")
    declarations: tuple[SurveyCompatibilityDeclaration, ...] = Field(max_length=1024)
