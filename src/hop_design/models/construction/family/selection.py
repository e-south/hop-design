"""Explicit comparative membership references verified construction authorities."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.comparisons.materials import PriorMaterialReuse
from hop_design.models.construction.stage_controls import ResolvedStageControl

from .request import SharedProperty


class ConstructionSetMember(HopModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,31}$")
    bundle_path: str = Field(min_length=1)
    selection_path: str = Field(min_length=1)


class ConstructionSetRequest(HopModel):
    schema_id: Literal["hop.construction-set/v1", "hop.construction-set/v2"] = Field(alias="schema")
    members: tuple[ConstructionSetMember, ...] = Field(min_length=1, max_length=64)
    baseline: str
    shared_properties: tuple[SharedProperty, ...]
    compared_properties: tuple[SharedProperty, ...]
    stage_controls: tuple[ResolvedStageControl, ...] = Field(
        default=(), max_length=192, exclude_if=lambda value: not value
    )
    reuse_prior_materials: PriorMaterialReuse | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def validate_membership(self) -> ConstructionSetRequest:
        names = [member.name for member in self.members]
        if len(names) != len(set(names)):
            raise ValueError("Set member names must be unique.")
        if self.baseline not in names:
            raise ValueError("Set baseline must name an explicit member.")
        properties = (*self.shared_properties, *self.compared_properties)
        if len(properties) != len(set(properties)):
            raise ValueError("Shared and compared properties must be distinct and not repeat.")
        if (
            self.stage_controls or self.reuse_prior_materials
        ) and self.schema_id == "hop.construction-set/v1":
            raise ValueError("Stage controls and prior-material reuse require construction-set/v2.")
        for control in self.stage_controls:
            if not set(control.members) <= set(names):
                raise ValueError("Stage control must reference existing set members.")
            if control.scope == "set" and set(control.members) != set(names):
                raise ValueError("Set-scoped control must include every selected member.")
        return self
