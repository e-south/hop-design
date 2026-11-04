"""Exact authored components needed before an endpoint has a discovery role."""

from pydantic import field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.sequence import normalize_dna_sequence


class ExactBasalArms(HopModel):
    """Two explicit basal arms, each written in its own 5-prime to 3-prime direction."""

    left_arm: str
    right_arm: str

    @field_validator("left_arm", "right_arm")
    @classmethod
    def normalize_arm(cls, value: str) -> str:
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_lengths(self) -> "ExactBasalArms":
        if len(self.left_arm) != len(self.right_arm):
            raise ValueError("Exact basal arms must have equal lengths.")
        return self
