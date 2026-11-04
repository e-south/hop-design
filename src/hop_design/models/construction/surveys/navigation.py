"""Strict resumable position in the finite geometry/context/page traversal."""

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class SurveySeekCursor(HopModel):
    schema_name: Literal["hop.interface-survey-seek/v1"] = Field(
        default="hop.interface-survey-seek/v1", alias="schema"
    )
    wave: int = Field(default=0, ge=0)
    context: int = Field(default=0, ge=0)
    geometry: tuple[int, int, int, int, int, int] | None = None
    page_after: int = Field(default=-1, ge=-1)
    wave_has_page: bool = False

    @model_validator(mode="after")
    def cursor_bounds(self) -> "SurveySeekCursor":
        if self.context > self.wave:
            raise ValueError("Seek context cannot exceed its traversal wave.")
        if self.geometry is not None and any(n < 0 for n in self.geometry):
            raise ValueError("Seek geometry coordinates must be nonnegative.")
        if self.page_after >= 0 and (self.geometry is None or not self.wave_has_page):
            raise ValueError("A continued page requires its geometry and a nonempty wave.")
        return self
