"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/binding.py

Binds one replay-verified source partition to exact complete-route states.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.payload import _content_id


class SourcePartitionBinding(HopModel):
    """Exact references joining one partition realization to one route replay."""

    binding_id: str = Field(pattern=r"^hop:source-partition-binding/[0-9a-f]{64}@1$")
    result_id: str = Field(pattern=r"^hop:source-partition-result/[0-9a-f]{64}@1$")
    realization_id: str = Field(
        pattern=r"^hop:source-partition-realization/[0-9a-f]{64}@1$"
    )
    source_preparation_product_state_id: str = Field(
        pattern=r"^hop:construction-state/[0-9a-f]{64}@1$"
    )
    top_material_use_id: str = Field(pattern=r"^hop:material-use/[0-9a-f]{64}@1$")
    bottom_material_use_id: str = Field(pattern=r"^hop:material-use/[0-9a-f]{64}@1$")
    reaction_program_id: str = Field(min_length=1)
    denatured_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")
    selected_state_id: str = Field(pattern=r"^hop:construction-state/[0-9a-f]{64}@1$")

    @classmethod
    def create(cls, **content: object) -> SourcePartitionBinding:
        draft = cls.model_construct(binding_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"binding_id"})
        return cls.model_validate(
            {"binding_id": _content_id("source-partition-binding", 1, seed), **content}
        )

    @model_validator(mode="after")
    def validate_identity(self) -> SourcePartitionBinding:
        content = self.model_dump(mode="json", exclude={"binding_id"})
        if self.binding_id != _content_id("source-partition-binding", 1, content):
            raise ValueError("Source-partition binding identity must seal exact route states.")
        if self.top_material_use_id == self.bottom_material_use_id:
            raise ValueError("Source-partition binding requires distinct prepared strand uses.")
        if self.denatured_state_id == self.selected_state_id:
            raise ValueError("Source partition must distinguish denatured and selected states.")
        return self


__all__ = ["SourcePartitionBinding"]
