"""Preserved insert selection wraps the existing exact survey address and reference."""

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel

from ..surveys.selection import InterfaceSurveySelection
from ..variants.query import Digest
from .refinement import DesignRefinementQuery


class InsertDesignSelection(HopModel):
    schema_id: Literal["hop.insert-design-selection/v1"] = Field(
        default="hop.insert-design-selection/v1", alias="schema"
    )
    request_digest: Digest
    snapshot_digest: Digest
    query_digest: Digest
    query: DesignRefinementQuery
    materialized_realization_id: str
    native: InterfaceSurveySelection
    reference: InterfaceSurveySelection
