"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/accounting.py

Defines whole-route composition accounting and reversible group replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import RealizationGroup, RealizationGrouping
from hop_design.models.construction.payload import _content_id


class CompositionAccounting(HopModel):
    """Exact nominal, rejected, accepted, geometry, and product counts."""

    foldback_local_realizations: int = Field(ge=0)
    basal_local_realizations: int = Field(ge=0)
    nominal_combinations: int = Field(ge=0)
    pruned_before_execution: int = Field(ge=0)
    executed_combinations: int = Field(ge=0)
    examined_combinations: int = Field(ge=0)
    rejected_after_execution: int = Field(ge=0)
    rejected_combinations: int = Field(ge=0)
    truncated_combinations: int = Field(ge=0)
    valid_realizations: int = Field(ge=0)
    candidate_enzyme_programs: int = Field(ge=0)
    recognition_placements_attempted: int = Field(ge=0)
    constraint_systems_attempted: int = Field(ge=0)
    distinct_geometry_groups: int = Field(ge=0)
    distinct_final_products: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> CompositionAccounting:
        if self.executed_combinations != self.examined_combinations:
            raise ValueError("Executed and examined composition counts must agree.")
        if self.rejected_after_execution != self.rejected_combinations:
            raise ValueError("Post-execution rejection counts must agree.")
        if self.examined_combinations != (
            self.rejected_combinations + self.truncated_combinations + self.valid_realizations
        ):
            raise ValueError(
                "Examined combinations must partition into rejected, truncated, and valid."
            )
        if self.examined_combinations > self.nominal_combinations:
            raise ValueError("Examined combinations cannot exceed the nominal Cartesian product.")
        if self.pruned_before_execution + self.executed_combinations > self.nominal_combinations:
            raise ValueError("Pruned and executed combinations cannot exceed the nominal product.")
        return self


def validate_realization_groups(
    groups: tuple[RealizationGroup, ...],
    realizations: tuple[Any, ...],
    grouping: RealizationGrouping,
) -> None:
    """Require unique, lossless groups whose keys replay their exact members."""
    realization_ids = tuple(item.materialized_realization_id for item in realizations)
    keys = tuple(group.group_key for group in groups)
    if len(keys) != len(set(keys)):
        raise ValueError("Construction group keys must be unique.")
    if keys != tuple(sorted(keys)):
        raise ValueError("Construction groups must use canonical key order.")
    grouped = tuple(item for group in groups for item in group.realization_ids)
    if any(group.grouping is not grouping for group in groups) or Counter(grouped) != Counter(
        realization_ids
    ):
        raise ValueError("Construction grouping must losslessly cover every realization.")
    expected: dict[str, list[str]] = {}
    for realization in realizations:
        key = (
            _content_id("geometry", 1, realization.geometry_ids)
            if grouping is RealizationGrouping.ACHIEVED_GEOMETRY
            else realization.final_product.reference.final_product_id
        )
        expected.setdefault(key, []).append(realization.materialized_realization_id)
    observed = {group.group_key: list(group.realization_ids) for group in groups}
    if observed != expected:
        raise ValueError("Construction groups must replay member semantics exactly.")


__all__ = ["CompositionAccounting", "validate_realization_groups"]
