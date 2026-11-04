"""A molecular color lens selects a recorded coordinate, never a requirement."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class AtlasColorLens(HopModel):
    key: Literal[
        "none",
        "left_gap",
        "right_gap",
        "loop_nt",
        "foldback_arm_bp",
        "loop_word",
        "left_end_word",
        "right_end_word",
    ]
    word: str | None = Field(default=None, pattern=r"^[ACGT]+$")

    @model_validator(mode="after")
    def exact_word(self) -> "AtlasColorLens":
        categorical = self.key in {"loop_word", "left_end_word", "right_end_word"}
        if categorical != (self.word is not None):
            raise ValueError("Sequence color views require an exact word; numeric views do not.")
        return self
