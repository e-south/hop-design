"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projections/navigation_geometry.py

Defines exact achieved-geometry groups for construction result navigation.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget


class ConstructionNavigationGeometryGroup(HopModel):
    """One scientifically described achieved-geometry group with exact membership."""

    group_key: str = Field(pattern=r"^hop:geometry/[0-9a-f]{64}@1$")
    foldback_geometry: FoldbackTarget
    basal_geometry: BasalTarget | None = None
    realization_ids: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def create(cls, **content: object) -> ConstructionNavigationGeometryGroup:
        draft = cls.model_construct(group_key="", **cast(Any, content))
        geometry_ids = (
            *((_geometry_id(draft.basal_geometry),) if draft.basal_geometry is not None else ()),
            _geometry_id(draft.foldback_geometry),
        )
        return cls.model_validate(
            {"group_key": _content_id("geometry", 1, geometry_ids), **content}
        )

    @model_validator(mode="after")
    def validate_group(self) -> ConstructionNavigationGeometryGroup:
        geometry_ids = (
            *((_geometry_id(self.basal_geometry),) if self.basal_geometry is not None else ()),
            _geometry_id(self.foldback_geometry),
        )
        if self.group_key != _content_id("geometry", 1, geometry_ids):
            raise ValueError("Navigation geometry group key must match its typed descriptors.")
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("Navigation geometry groups cannot repeat a realization.")
        return self


def _geometry_id(geometry: FoldbackTarget | BasalTarget) -> str:
    return _content_id("geometry", 1, geometry.model_dump(mode="json"))


__all__ = ["ConstructionNavigationGeometryGroup"]
