"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/selection.py

Replays inclusive source-fragment selection against complete-route states.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter

from hop_design.models.construction.complete.state import ConstructionState
from hop_design.models.construction.source_partition.result import (
    SourcePartitionDiscoveryResult,
    SourcePartitionRealization,
)

from .errors import SourcePartitionBindingError, SourcePartitionBindingFailure
from .facts import partition_fragment_fact, route_fragment_fact


def validate_partition_selection(
    *,
    realization: SourcePartitionRealization,
    partition_result: SourcePartitionDiscoveryResult,
    denatured_state: ConstructionState,
    selected_state: ConstructionState,
    source_length: int,
    top_use_id: str,
    bottom_use_id: str,
) -> None:
    """Require exact partition membership and route-state fragment equivalence."""
    fragments = {item.fragment_id: item for item in realization.denatured.fragments}
    retained_ids = realization.selected.retained_fragment_ids
    excluded_ids = realization.selected.excluded_fragment_ids
    if set(retained_ids) | set(excluded_ids) != set(fragments) or set(retained_ids) & set(
        excluded_ids
    ):
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "Partition evidence must divide every denatured fragment exactly once.",
        )
    selection = realization.selected.selection
    expected_retained = tuple(
        fragment_id
        for fragment_id, fragment in fragments.items()
        if len(fragment.sequence) >= selection.min_length_nt
        and (selection.max_length_nt is None or len(fragment.sequence) <= selection.max_length_nt)
    )
    if retained_ids != expected_retained:
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "Partition evidence must replay the inclusive length-selection rule.",
        )
    required = Counter(
        (item.precursor_strand, item.source_span.start.offset, item.source_span.end.offset)
        for item in partition_result.request.constraints.required_survivors
    )
    retained = Counter(
        (
            fragments[item].precursor_strand,
            fragments[item].precursor_span.start.offset,
            fragments[item].precursor_span.end.offset,
        )
        for item in retained_ids
    )
    if required != retained:
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "Required survivors must equal the retained partition exactly.",
        )
    partition_denatured = Counter(
        partition_fragment_fact(item) for item in realization.denatured.fragments
    )
    route_denatured = Counter(
        route_fragment_fact(
            item,
            source_length=source_length,
            top_use_id=top_use_id,
            bottom_use_id=bottom_use_id,
        )
        for item in denatured_state.molecules
    )
    route_selected = Counter(
        route_fragment_fact(
            item,
            source_length=source_length,
            top_use_id=top_use_id,
            bottom_use_id=bottom_use_id,
        )
        for item in selected_state.molecules
    )
    expected_selected = Counter(partition_fragment_fact(fragments[item]) for item in retained_ids)
    if route_denatured != partition_denatured or route_selected != expected_selected:
        raise SourcePartitionBindingError(
            SourcePartitionBindingFailure.SELECTION_INCOMPATIBLE,
            "Route denaturation and selected survivors must equal partition molecular facts.",
        )


__all__ = ["validate_partition_selection"]
