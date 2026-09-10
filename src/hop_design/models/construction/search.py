"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/search.py

Defines finite retained-overhead search plans and foldback geometry domains.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.junction import Strand

from .basal_release import BasalFutureReleaseRequirement
from .sequence_domain import SequenceDomainPartition
from .targets import (
    BasalPairConstraint,
    BasalTarget,
    FoldbackTarget,
    NickStrandSelection,
)


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
    sequence_partition: SequenceDomainPartition | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_stop_policy(self) -> NeighborhoodSearchPlan:
        if (self.stop is SearchStopMode.RESULT_QUOTA) != (self.result_quota is not None):
            raise ValueError("result_quota stopping requires one explicit result_quota.")
        return self


class FoldbackGeometryDomain(HopModel):
    """Finite structural constraints for overhead-ordered foldback discovery."""

    family: Literal["foldback"] = "foldback"
    nick_strand: Strand | NickStrandSelection = NickStrandSelection.ANY
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


class BasalGeometryDomain(HopModel):
    """Finite state-aware constraints for retained-overhead basal discovery."""

    family: Literal["basal"] = "basal"
    nick_strand: Strand | NickStrandSelection = NickStrandSelection.ANY
    nick_offsets_nt: tuple[int, ...] = (0,)
    pairing_constraints: tuple[BasalPairConstraint, ...] = Field(min_length=1)
    max_noncanonical_pairs: int | None = Field(
        default=None, ge=0, exclude_if=lambda value: value is None
    )
    minimum_adapter_annealing_nt: int = Field(default=15, ge=1)
    mismatch_warning_fraction: float = Field(default=0.20, ge=0.0, le=1.0)
    future_release: BasalFutureReleaseRequirement | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )

    @field_validator("nick_offsets_nt", mode="after")
    @classmethod
    def canonicalize_offsets(cls, values: tuple[int, ...]) -> tuple[int, ...]:
        if not values:
            raise ValueError("Basal discovery requires a finite nick-offset domain.")
        if any(value < 0 for value in values):
            raise ValueError("Basal nick offsets must be nonnegative.")
        if len(values) != len(set(values)):
            raise ValueError("Basal nick offsets must not repeat values.")
        return tuple(sorted(values))

    @model_validator(mode="after")
    def validate_cardinality(self) -> BasalGeometryDomain:
        end_count = 1 if self.future_release is None else self.future_release.cardinality
        if len(self.nick_offsets_nt) * end_count > 100_000:
            raise ValueError("A geometry domain may contain at most 100000 exact basal targets.")
        return self

    def exact_targets(self) -> Iterator[BasalTarget]:
        """Yield targets in offset then exact cohesive-end sequence order."""
        for offset in self.nick_offsets_nt:
            releases = (
                (None,) if self.future_release is None else self.future_release.exact_requirements()
            )
            for release in releases:
                yield BasalTarget(
                    nick_strand=self.nick_strand,
                    nick_offset_nt=offset,
                    pairing_constraints=self.pairing_constraints,
                    max_noncanonical_pairs=self.max_noncanonical_pairs,
                    ligation_proximal_match_required=True,
                    future_release=release,
                )


LocalGeometryDomain = Annotated[
    FoldbackGeometryDomain | BasalGeometryDomain,
    Field(discriminator="family"),
]


class FoldbackOverheadLevel(HopModel):
    """Every admissible foldback geometry at one absolute retained-overhead level."""

    retained_overhead_nt: int = Field(ge=0)
    geometries: tuple[FoldbackTarget, ...]


__all__ = [
    "BasalGeometryDomain",
    "FoldbackGeometryDomain",
    "FoldbackOverheadLevel",
    "LocalGeometryDomain",
    "NeighborhoodSearchPlan",
    "SearchScope",
    "SearchStopMode",
]
