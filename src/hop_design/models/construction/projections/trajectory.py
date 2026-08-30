"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/trajectory.py

Defines one exact selected trajectory from a verified construction result.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.complete import MaterializedConstructionRealization
from hop_design.models.construction.payload import _content_id

COMPLETE_CONSTRUCTION_TRAJECTORY_RENDERER_VERSION: Literal["complete-construction-trajectory/1"] = (
    "complete-construction-trajectory/1"
)


class CompleteConstructionTrajectoryProjection(HopModel):
    """One caller-selected accepted route embedded without scientific reduction."""

    schema_id: Literal["hop.complete-construction-trajectory/v2"] = Field(
        default="hop.complete-construction-trajectory/v2",
        alias="schema",
    )
    projection_id: str = Field(pattern=r"^hop:complete-construction-trajectory/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:construction-space-result/[0-9a-f]{64}@1$")
    renderer_version: Literal["complete-construction-trajectory/1"] = (
        COMPLETE_CONSTRUCTION_TRAJECTORY_RENDERER_VERSION
    )
    composition_ordinal: int = Field(ge=0)
    realization: MaterializedConstructionRealization

    @classmethod
    def create(cls, **content: object) -> CompleteConstructionTrajectoryProjection:
        draft = cls.model_construct(projection_id="", **cast(Any, content))
        return cls.model_validate({"projection_id": draft._expected_projection_id(), **content})

    def _expected_projection_id(self) -> str:
        return _content_id(
            "complete-construction-trajectory",
            1,
            self.model_dump(mode="json", by_alias=True, exclude={"projection_id"}),
        )

    @model_validator(mode="after")
    def validate_projection(self) -> CompleteConstructionTrajectoryProjection:
        if self.projection_id != self._expected_projection_id():
            raise ValueError("projection_id must seal the complete trajectory relation.")
        return self


__all__ = [
    "COMPLETE_CONSTRUCTION_TRAJECTORY_RENDERER_VERSION",
    "CompleteConstructionTrajectoryProjection",
]
