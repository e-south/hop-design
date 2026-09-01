"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/navigation.py

Defines a sealed navigation projection around a complete construction summary.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.complete.authority import CompositionDispositionStatus
from hop_design.models.construction.payload import _content_id

from .complete import CompleteConstructionSummaryProjection
from .navigation_geometry import ConstructionNavigationGeometryGroup
from .navigation_route import ConstructionNavigationAcceptedRoute

CONSTRUCTION_NAVIGATION_RENDERER_VERSION: Literal["construction-navigation/1"] = (
    "construction-navigation/1"
)


class ConstructionNavigationProjection(HopModel):
    """Additive browse facts over one unchanged complete construction summary."""

    schema_id: Literal["hop.construction-navigation/v1"] = Field(
        default="hop.construction-navigation/v1",
        alias="schema",
    )
    projection_id: str = Field(pattern=r"^hop:construction-navigation/[0-9a-f]{64}@1$")
    source_result_id: str = Field(pattern=r"^hop:construction-space-result/[0-9a-f]{64}@1$")
    renderer_version: Literal["construction-navigation/1"] = (
        CONSTRUCTION_NAVIGATION_RENDERER_VERSION
    )
    summary: CompleteConstructionSummaryProjection
    accepted_routes: tuple[ConstructionNavigationAcceptedRoute, ...]
    geometry_groups: tuple[ConstructionNavigationGeometryGroup, ...]

    @classmethod
    def create(cls, **content: object) -> ConstructionNavigationProjection:
        draft = cls.model_construct(projection_id="", **cast(Any, content))
        return cls.model_validate({"projection_id": draft._expected_projection_id(), **content})

    def _expected_projection_id(self) -> str:
        return _content_id(
            "construction-navigation",
            1,
            self.model_dump(mode="json", by_alias=True, exclude={"projection_id"}),
        )

    @model_validator(mode="after")
    def validate_navigation(self) -> ConstructionNavigationProjection:
        if self.source_result_id != self.summary.source_result_id:
            raise ValueError("Navigation and summary must reference the same source result.")
        accepted_summary_ids = tuple(
            cast(str, row.materialized_realization_id)
            for row in self.summary.rows
            if row.status is CompositionDispositionStatus.ACCEPTED
        )
        accepted_route_ids = tuple(
            route.materialized_realization_id for route in self.accepted_routes
        )
        if accepted_route_ids != accepted_summary_ids:
            raise ValueError("Navigation routes must preserve accepted summary order exactly.")
        summary_groups = tuple(
            (group.group_key, group.realization_ids) for group in self.summary.geometry_groups
        )
        navigation_groups = tuple(
            (group.group_key, group.realization_ids) for group in self.geometry_groups
        )
        if navigation_groups != summary_groups:
            raise ValueError(
                "Navigation geometry groups must preserve summary keys and membership order."
            )
        routes_by_id = {route.materialized_realization_id: route for route in self.accepted_routes}
        if any(
            routes_by_id[realization_id].foldback_geometry != group.foldback_geometry
            or routes_by_id[realization_id].basal_geometry != group.basal_geometry
            for group in self.geometry_groups
            for realization_id in group.realization_ids
        ):
            raise ValueError("Navigation group geometry must match every accepted route.")
        if self.projection_id != self._expected_projection_id():
            raise ValueError("projection_id must seal the construction navigation relation.")
        return self


__all__ = [
    "CONSTRUCTION_NAVIGATION_RENDERER_VERSION",
    "ConstructionNavigationAcceptedRoute",
    "ConstructionNavigationGeometryGroup",
    "ConstructionNavigationProjection",
]
