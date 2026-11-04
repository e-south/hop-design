"""Regional equality requirements name their molecular stage and membership."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

type StageProperty = Literal["non_loop_sequences", "non_loop_pairing", "terminal_chemistry"]


class StageControl(HopModel):
    property: StageProperty
    stage: Literal["hairpin", "endpoint"]
    scope: Literal["set", "group"]
    group: str | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def explicit_scope(self) -> StageControl:
        if (self.scope == "group") != (self.group is not None):
            raise ValueError("A group-scoped control must name exactly one comparison group.")
        return self


class ResolvedStageControl(StageControl):
    """Portable selection binds scope to exact, explicit member names."""

    members: tuple[str, ...] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_members(self) -> ResolvedStageControl:
        if len(self.members) != len(set(self.members)):
            raise ValueError("Stage-control member names must not repeat.")
        return self
