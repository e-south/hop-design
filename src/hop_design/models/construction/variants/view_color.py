"""A molecular color lens selects a recorded coordinate, never a requirement."""

from collections.abc import Mapping
from math import isfinite
from typing import Any, Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class AtlasColorLens(HopModel):
    key: Literal[
        "none",
        "left_gap",
        "right_gap",
        "max_end_gap",
        "released_non_stem_nt",
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

    def value_in(
        self, values: Mapping[str, Any], *, overhead: Mapping[str, Any] | None = None
    ) -> Any:
        """Read a color measurement without changing the recorded coordinates."""
        if self.key == "released_non_stem_nt":
            strands = (overhead or {}).get("endpoint_non_payload_nt_by_strand")
            if strands is None or (isinstance(strands, Mapping) and len(strands) != 2):
                return None
            if not isinstance(strands, Mapping) or any(
                isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in strands.values()
            ):
                raise ValueError(
                    "Released-insert color requires nonnegative strand nucleotide counts."
                )
            return sum(strands.values())
        if self.key != "max_end_gap":
            return values.get(self.key)
        ends = [values.get(key) for key in ("left_gap", "right_gap")]
        if None in ends:
            return None
        measurements: list[int | float] = []
        for value in ends:
            if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(value):
                raise ValueError("End-gap color requires finite numeric measurements.")
            measurements.append(value)
        return max(measurements)
