"""Interleave unfinished completions with new groups and other local pairs."""

from hop_design.models.construction.surveys.completion import (
    CompletionAttemptCursor,
    CompletionFrontierEntry,
    CompletionSeekCursor,
    CompletionWork,
)

from ..coordinates import coordinate_at
from ..geometry_order import GeometryOrder
from .navigation import CompletionFrontierLimitError


def schedule_followups(
    attempt: CompletionAttemptCursor,
    *,
    order: GeometryOrder,
    recorded_pairs: int,
    next_member: int | None,
    exclusions: tuple[str, ...],
    maximum_frontier: int,
) -> CompletionSeekCursor:
    """Keep one pending word per pair and introduce further pairs lazily.

    Priority adds pair ordinal and attempts already made to the group's original
    geometry/depth/group cost. Every finite task has finitely many predecessors;
    a huge unresolved completion domain cannot hold the next group or pair.
    A learned skip advances the member address without artificially increasing
    its scheduling cost by the cardinality of the excluded sequence subset.
    """
    if type(recorded_pairs) is not int or recorded_pairs < 0:
        raise ValueError("Recorded pair count must be nonnegative.")
    pending = []
    if attempt.iteration == 0 and attempt.pair + 1 < recorded_pairs:
        pending.append(CompletionWork(pair=attempt.pair + 1))
    if next_member is not None:
        if next_member <= attempt.member:
            raise ValueError("A retry must advance the exact completion address.")
        pending.append(
            CompletionWork(
                pair=attempt.pair,
                member=next_member,
                iteration=attempt.iteration + 1,
                excluded_context_patterns=exclusions,
            )
        )
    sizes = tuple(len(c) for c in order.costs)
    geometry = coordinate_at(sizes, attempt.geometry_rank)
    entries = list(attempt.after.frontier)
    for work in pending:
        entries.append(
            CompletionFrontierEntry.model_validate(
                {
                    "kind": "work",
                    "geometry": geometry,
                    "wave": order.cost(geometry)
                    + attempt.depth
                    + attempt.group
                    + work.pair
                    + work.iteration,
                    "depth": attempt.depth,
                    "page": attempt.page,
                    "group": attempt.group,
                    "work": work,
                }
            )
        )
    if type(maximum_frontier) is not int or not 1 <= maximum_frontier <= 100_000:
        raise ValueError("Completion frontier bound must be between 1 and 100000 entries.")
    if len(entries) > maximum_frontier:
        raise CompletionFrontierLimitError("Pending completion work exceeds the frontier bound.")
    return attempt.after.model_copy(
        update={"initialized": True, "frontier": tuple(sorted(entries, key=lambda e: e.priority()))}
    )
