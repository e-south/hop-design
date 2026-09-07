"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/search.py

Defines finite retained-overhead search plans and foldback geometry domains.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel

from .targets import FoldbackTarget, NickStrandSelection


class SearchStopMode(StrEnum):
    """Declared stopping behavior for one finite neighborhood search."""

    EXHAUSTIVE = "exhaustive"
    RESULT_QUOTA = "result_quota"


class SearchScope(StrEnum):
    """Claim scope requested from one finite neighborhood search."""

    EXISTENCE = "existence"
    ALL_REALIZATIONS = "all_realizations"


class NeighborhoodSearchPlan(HopModel):
    """Finite execution and coverage policy for retained-overhead discovery."""

    max_retained_overhead_nt: int = Field(ge=0)
    max_search_nodes: int = Field(ge=1, le=100_000)
    max_realizations: int = Field(ge=1, le=100_000)
    scope: SearchScope = SearchScope.ALL_REALIZATIONS
    stop: SearchStopMode = SearchStopMode.EXHAUSTIVE
    result_quota: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_stop_policy(self) -> NeighborhoodSearchPlan:
        if (self.stop is SearchStopMode.RESULT_QUOTA) != (self.result_quota is not None):
            raise ValueError("result_quota stopping requires one explicit result_quota.")
        return self


class FoldbackGeometryDomain(HopModel):
    """Finite structural constraints for overhead-ordered foldback discovery."""

    nick_strand: NickStrandSelection = NickStrandSelection.ANY
    junction_offsets_nt: tuple[int, ...] = (0,)
    minimum_loop_length_nt: int = Field(default=3, ge=3)
    minimum_annealing_arm_length_bp: int = Field(default=3, ge=3)
    loop_lengths_nt: tuple[int, ...] = ()
    annealing_arm_lengths_bp: tuple[int, ...] = ()

    @field_validator(
        "junction_offsets_nt",
        "loop_lengths_nt",
        "annealing_arm_lengths_bp",
        mode="after",
    )
    @classmethod
    def canonicalize_values(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if any(value < 0 for value in values):
            raise ValueError("Foldback geometry values must be nonnegative.")
        if len(values) != len(set(values)):
            raise ValueError("Foldback geometry domains must not repeat values.")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def validate_domain(self) -> FoldbackGeometryDomain:
        if not self.junction_offsets_nt:
            raise ValueError("Foldback discovery requires a finite junction-offset domain.")
        if self.loop_lengths_nt and min(self.loop_lengths_nt) < self.minimum_loop_length_nt:
            raise ValueError("Foldback loop lengths must satisfy the declared structural floor.")
        if (
            self.annealing_arm_lengths_bp
            and min(self.annealing_arm_lengths_bp) < self.minimum_annealing_arm_length_bp
        ):
            raise ValueError(
                "Foldback annealing-arm lengths must satisfy the declared structural floor."
            )
        return self


class FoldbackOverheadLevel(HopModel):
    """Every admissible foldback geometry at one absolute retained-overhead level."""

    retained_overhead_nt: int = Field(ge=0)
    geometries: tuple[FoldbackTarget, ...]


__all__ = [
    "FoldbackGeometryDomain",
    "FoldbackOverheadLevel",
    "NeighborhoodSearchPlan",
    "SearchScope",
    "SearchStopMode",
]
