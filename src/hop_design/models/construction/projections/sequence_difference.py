"""A literal regional sequence comparison, with explicit correspondence limits."""

from typing import Literal

from hop_design.models.base import HopModel


class SequenceComparisonColumn(HopModel):
    kind: Literal["unchanged", "substitution", "added", "removed"]
    reference_offset: int | None
    observed_offset: int | None
    reference_base: str | None
    observed_base: str | None


class SequenceRegionDifference(HopModel):
    region: str
    reference_sequence: str
    observed_sequence: str
    reference_span: tuple[int, int]
    observed_span: tuple[int, int]
    coordinates_changed: bool
    length_delta: int
    correspondence: Literal[
        "identical", "unique_minimum_edit", "ambiguous_minimum_edit", "unresolved_budget"
    ]
    columns: tuple[SequenceComparisonColumn, ...]
