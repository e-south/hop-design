"""Name-free molecular selectors direct search without changing permission domains."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.scaffold import ScaffoldDimension
from hop_design.models.sequence import normalize_dna_sequence

from .placement import EndPlacement


class ScaffoldSearchTarget(HopModel):
    end_placement: EndPlacement | None = Field(default=None, exclude_if=lambda v: v is None)
    basal_nick_enzyme_id: str | None = Field(default=None, exclude_if=lambda v: v is None)
    dimensions: dict[ScaffoldDimension, Annotated[int, Field(ge=0)]] = Field(default_factory=dict)
    release_enzyme_id: str | None = None
    loop_sequence: str | None = None

    @field_validator("loop_sequence")
    @classmethod
    def exact_word(cls, value: str | None) -> str | None:
        return None if value is None else normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def meaningful_selector(self) -> ScaffoldSearchTarget:
        if (
            not self.dimensions
            and self.release_enzyme_id is None
            and self.loop_sequence is None
            and self.end_placement is None
            and self.basal_nick_enzyme_id is None
        ):
            raise ValueError("A search target needs a dimension, loop sequence or method.")
        if self.loop_sequence is not None and self.dimensions.get(
            "loop_nt", len(self.loop_sequence)
        ) != len(self.loop_sequence):
            raise ValueError("Target loop sequence and dimension disagree.")
        return self
