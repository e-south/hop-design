"""A concise authoring document that compiles to the existing family request."""

from typing import Literal

from pydantic import Field

from hop_design.models.base import HopModel
from hop_design.models.construction.complete.source_preparation import (
    LinearSourceMaterializationSpec,
)
from hop_design.models.construction.payload import ConstructionEndpoint
from hop_design.models.construction.scaffold import HairpinScaffoldRequirements

from .request import FamilyBounds, ScaffoldDisplayPreference, ScaffoldFamilyMember, SharedProperty


class ScaffoldGeometryPermissions(HopModel):
    loop_nt: tuple[int, ...] | None = Field(default=None, min_length=1, max_length=64)
    loop_side_paired_bp: tuple[int, ...] | None = Field(default=None, min_length=1, max_length=64)


class ScaffoldComparisonBrief(HopModel):
    schema_id: Literal["hop.scaffold-comparison/v1"] = Field(alias="schema")
    base_request: str = Field(min_length=1)
    product: ConstructionEndpoint
    vary: tuple[ScaffoldFamilyMember, ...] = Field(min_length=1, max_length=64)
    hold: tuple[SharedProperty, ...]
    geometry_permissions: ScaffoldGeometryPermissions = ScaffoldGeometryPermissions()
    requirements: HairpinScaffoldRequirements | None = None
    materials: LinearSourceMaterializationSpec | None = None
    display_preferences: tuple[ScaffoldDisplayPreference, ...] = ()
    bounds: FamilyBounds
