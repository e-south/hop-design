"""Desired comparative membership over achieved complete-product dimensions."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from .family.request import ScaffoldDimension, SharedProperty


class OptionSetMember(HopModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,31}$")
    dimensions: dict[ScaffoldDimension, Annotated[int, Field(ge=0)]] = Field(min_length=1)


class ScaffoldComparisonRequest(HopModel):
    schema_id: Literal["hop.scaffold-comparison/v1"] = Field(alias="schema")
    members: tuple[OptionSetMember, ...] = Field(min_length=2, max_length=64)
    shared_properties: tuple[SharedProperty, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_meaningful_comparison(self) -> ScaffoldComparisonRequest:
        names = [m.name for m in self.members]
        dimensions = [m.dimensions for m in self.members]
        if len(set(names)) != len(names):
            raise ValueError("Comparison member names must be unique.")
        if any(set(d) != set(dimensions[0]) for d in dimensions):
            raise ValueError("Every member must declare the same comparison dimensions.")
        if len({tuple(sorted(d.items())) for d in dimensions}) != len(dimensions):
            raise ValueError("Each requested member must have a distinct dimension combination.")
        if len(set(self.shared_properties)) != len(self.shared_properties):
            raise ValueError("Shared properties must not repeat.")
        for key in dimensions[0]:
            if key in self.shared_properties and len({d[key] for d in dimensions}) > 1:
                raise ValueError(f"Comparison varies {key} but also requires it to remain shared.")
        return self
