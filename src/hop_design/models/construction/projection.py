"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/projection.py

Defines payload-centered construction contracts and discovery evidence.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

from .accounting import RealizationGroup
from .payload import _content_id


class ProjectionReference(HopModel):
    """Non-authoritative grouping projection that preserves exact realization membership."""

    projection_id: str = Field(pattern=r"^hop:projection/[0-9a-f]{64}@1$")
    result_id: str = Field(
        pattern=(
            r"^hop:(?:neighborhood-result|foldback-neighborhood-result|"
            r"basal-neighborhood-result|construction-result)/[0-9a-f]{64}@1$"
        )
    )
    projection_schema: str
    renderer_version: str
    realization_ids: tuple[str, ...]
    groups: tuple[RealizationGroup, ...]

    @model_validator(mode="after")
    def validate_projection(self) -> ProjectionReference:
        if len(self.realization_ids) != len(set(self.realization_ids)):
            raise ValueError("Projection realization ids must be unique.")
        grouped_ids = tuple(member for group in self.groups for member in group.realization_ids)
        if Counter(grouped_ids) != Counter(self.realization_ids) or len(grouped_ids) != len(
            set(grouped_ids)
        ):
            raise ValueError("Projection groups must cover every realization exactly once.")
        grouping_dimensions = {group.grouping for group in self.groups}
        if len(grouping_dimensions) > 1:
            raise ValueError("One projection must use one grouping dimension.")
        expected = _content_id(
            "projection",
            1,
            {
                "result_id": self.result_id,
                "projection_schema": self.projection_schema,
                "renderer_version": self.renderer_version,
                "realization_ids": self.realization_ids,
                "groups": [group.model_dump(mode="json") for group in self.groups],
            },
        )
        if self.projection_id != expected:
            raise ValueError("projection_id must replay from the complete projection relation.")
        return self


def grouped_realization_projection(
    *,
    result_id: str,
    projection_schema: str,
    renderer_version: str,
    realization_ids: tuple[str, ...],
    groups: tuple[RealizationGroup, ...],
) -> ProjectionReference:
    """Create a grouping projection only when its groups exactly cover the source relation."""
    grouped_ids = tuple(member for group in groups for member in group.realization_ids)
    if Counter(grouped_ids) != Counter(realization_ids) or len(grouped_ids) != len(
        set(grouped_ids)
    ):
        raise ValueError("Projection groups must cover every realization exactly once.")
    content = {
        "result_id": result_id,
        "projection_schema": projection_schema,
        "renderer_version": renderer_version,
        "realization_ids": realization_ids,
        "groups": [group.model_dump(mode="json") for group in groups],
    }
    return ProjectionReference(
        projection_id=_content_id("projection", 1, content),
        result_id=result_id,
        projection_schema=projection_schema,
        renderer_version=renderer_version,
        realization_ids=realization_ids,
        groups=groups,
    )
