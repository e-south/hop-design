"""Portable, non-authoritative reference to one query-matching complete preparation."""

from typing import Annotated, Literal

from pydantic import Field

from hop_design.models.base import HopModel

from .query import InterfaceSurveyQuery

Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class SurveyAddress(HopModel):
    target: int = Field(ge=0)
    step: int = Field(ge=0)


class InterfaceSurveySelection(HopModel):
    schema_id: Literal["hop.interface-survey-selection/v1"] = Field(
        default="hop.interface-survey-selection/v1", alias="schema"
    )
    request_digest: Digest
    snapshot_digest: Digest
    query_digest: Digest
    record_digest: Digest
    query: InterfaceSurveyQuery
    address: SurveyAddress
    materialized_realization_id: str = Field(min_length=1)
