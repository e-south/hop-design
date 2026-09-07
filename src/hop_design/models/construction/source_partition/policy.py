"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/policy.py

Defines exact sacrificial-fragment thresholds and their feasibility assessments.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import Field, model_validator

from hop_design.models.base import HopModel


class SacrificialFragmentPolicy(HopModel):
    """Inclusive preferred-to-absolute maximum fragment-length ladder."""

    preferred_maximum_nt: int = Field(ge=1)
    absolute_maximum_nt: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> SacrificialFragmentPolicy:
        if self.absolute_maximum_nt < self.preferred_maximum_nt:
            raise ValueError("Absolute fragment maximum must not be below the preferred maximum.")
        return self

    @property
    def thresholds(self) -> tuple[int, ...]:
        """Return every permitted inclusive maximum in canonical order."""
        return tuple(range(self.preferred_maximum_nt, self.absolute_maximum_nt + 1))


class SourcePartitionThresholdAssessment(HopModel):
    """Exact feasibility of one inclusive sacrificial-fragment maximum."""

    maximum_sacrificial_fragment_nt: int = Field(ge=1)
    feasible: bool
    violating_fragment_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_assessment(self) -> SourcePartitionThresholdAssessment:
        if self.violating_fragment_ids != tuple(sorted(set(self.violating_fragment_ids))):
            raise ValueError("Threshold violations must use unique canonical fragment ids.")
        if self.feasible == bool(self.violating_fragment_ids):
            raise ValueError("Threshold feasibility must agree with its fragment violations.")
        return self


__all__ = ["SacrificialFragmentPolicy", "SourcePartitionThresholdAssessment"]
