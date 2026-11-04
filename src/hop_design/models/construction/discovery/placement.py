"""Product-space end placements; distances are paired gaps, not source coordinates."""

from pydantic import Field

from hop_design.models.base import HopModel


class EndPlacement(HopModel):
    left_bp: int = Field(ge=0)
    right_bp: int = Field(ge=0)
