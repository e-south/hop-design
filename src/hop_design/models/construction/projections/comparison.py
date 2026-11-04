"""Recorded property differences between two explicit complete selections."""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field, JsonValue, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.complete.material import MaterialUseRole
from hop_design.models.construction.payload import _content_id

from .comparison_assessment import ComparisonAssessment, assess_comparison


class ComparisonSelection(HopModel):
    source_result_id: str = Field(pattern=r"^hop:construction-space-result/[0-9a-f]{64}@1$")
    materialized_realization_id: str = Field(
        pattern=r"^hop:materialized-construction/[0-9a-f]{64}@1$"
    )
    composition_status: str


class PropertyComparison(HopModel):
    """Values refer to the same named property, not necessarily the same coordinates."""

    field: str = Field(min_length=1)
    label: str = Field(min_length=1)
    left: JsonValue
    right: JsonValue
    changed: bool

    @model_validator(mode="after")
    def validate_difference(self) -> PropertyComparison:
        if self.changed != (self.left != self.right):
            raise ValueError("Property comparison must agree with the recorded values.")
        return self


class ConstructionComparisonProjection(HopModel):
    """Non-authoritative, content-bound comparison; it makes no performance ranking."""

    schema_id: Literal["hop.construction-comparison/v2"] = Field(
        default="hop.construction-comparison/v2", alias="schema"
    )
    projection_id: str = Field(pattern=r"^hop:construction-comparison/[0-9a-f]{64}@2$")
    left: ComparisonSelection
    right: ComparisonSelection
    properties: tuple[PropertyComparison, ...]
    changed_material_roles: tuple[MaterialUseRole, ...]
    unchanged_material_roles: tuple[MaterialUseRole, ...]
    assessment: ComparisonAssessment

    @classmethod
    def create(cls, **content: object) -> ConstructionComparisonProjection:
        content["assessment"] = assess_comparison(
            cast(tuple[PropertyComparison, ...], content["properties"])
        )
        draft = cls.model_construct(projection_id="", **cast(Any, content))
        return cls.model_validate({"projection_id": draft._expected_id(), **content})

    def _expected_id(self) -> str:
        return _content_id(
            "construction-comparison",
            2,
            self.model_dump(mode="json", by_alias=True, exclude={"projection_id"}),
        )

    @model_validator(mode="after")
    def validate_identity(self) -> ConstructionComparisonProjection:
        keys = [p.field for p in self.properties]
        if len(set(keys)) != len(keys):
            raise ValueError("Comparison properties must have unique fields.")
        if set(self.changed_material_roles) & set(self.unchanged_material_roles):
            raise ValueError("A material role cannot be both changed and unchanged.")
        if self.assessment != assess_comparison(self.properties):
            raise ValueError("Comparison assessment must agree with its recorded properties.")
        if self.projection_id != self._expected_id():
            raise ValueError("Comparison identity must bind both selections and their facts.")
        return self
