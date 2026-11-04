"""Bounded literal edit correspondence; ambiguity never becomes a specific edit claim."""

from functools import lru_cache
from typing import TypedDict

from hop_design.models.construction.projections.sequence_difference import (
    SequenceComparisonColumn,
    SequenceRegionDifference,
)


class _RegionFacts(TypedDict):
    region: str
    reference_sequence: str
    observed_sequence: str
    reference_span: tuple[int, int]
    observed_span: tuple[int, int]
    coordinates_changed: bool
    length_delta: int


@lru_cache(maxsize=64)
def compare_sequence_region(
    region: str,
    before: str,
    after: str,
    reference_span: tuple[int, int],
    observed_span: tuple[int, int],
) -> SequenceRegionDifference:
    """Align within a named 5-prime to 3-prime region, not across arbitrary whole-molecule offsets.

    Unique unit-cost minimum edit alignment is a display correspondence, not
    evidence of physical mutation, ancestry or a uniquely required redesign.
    """
    for sequence, span in ((before, reference_span), (after, observed_span)):
        if span[0] < 0 or span[1] - span[0] != len(sequence):
            raise ValueError("Compared region spans must match their literal sequence lengths.")
    m, n = len(before), len(after)
    common: _RegionFacts = {
        "region": region,
        "reference_sequence": before,
        "observed_sequence": after,
        "reference_span": reference_span,
        "observed_span": observed_span,
        "coordinates_changed": reference_span != observed_span,
        "length_delta": n - m,
    }
    if (m + 1) * (n + 1) > 65_536:
        return SequenceRegionDifference(**common, correspondence="unresolved_budget", columns=())
    if before == after:
        # Zero edits has a unique positional correspondence, even for repeated bases.
        # Preserve the display budget above and avoid a quadratic alignment for self views.
        return SequenceRegionDifference(
            **common,
            correspondence="identical",
            columns=tuple(
                SequenceComparisonColumn(
                    kind="unchanged",
                    reference_offset=i,
                    observed_offset=i,
                    reference_base=base,
                    observed_base=base,
                )
                for i, base in enumerate(before)
            ),
        )
    cost = [[0] * (n + 1) for _ in range(m + 1)]
    ways = [[0] * (n + 1) for _ in range(m + 1)]
    ways[m][n] = 1
    for i in range(m, -1, -1):
        for j in range(n, -1, -1):
            if i == m and j == n:
                continue
            candidates = []
            if i < m and j < n:
                candidates.append(
                    (cost[i + 1][j + 1] + (before[i] != after[j]), ways[i + 1][j + 1])
                )
            if i < m:
                candidates.append((cost[i + 1][j] + 1, ways[i + 1][j]))
            if j < n:
                candidates.append((cost[i][j + 1] + 1, ways[i][j + 1]))
            cost[i][j] = min(c for c, _ in candidates)
            ways[i][j] = min(2, sum(w for c, w in candidates if c == cost[i][j]))
    if ways[0][0] != 1:
        return SequenceRegionDifference(
            **common, correspondence="ambiguous_minimum_edit", columns=()
        )
    columns = []
    i = j = 0
    while i < m or j < n:
        if i < m and j < n and cost[i][j] == cost[i + 1][j + 1] + (before[i] != after[j]):
            columns.append(
                SequenceComparisonColumn(
                    kind="unchanged" if before[i] == after[j] else "substitution",
                    reference_offset=i,
                    observed_offset=j,
                    reference_base=before[i],
                    observed_base=after[j],
                )
            )
            i += 1
            j += 1
        elif i < m and cost[i][j] == cost[i + 1][j] + 1:
            columns.append(
                SequenceComparisonColumn(
                    kind="removed",
                    reference_offset=i,
                    observed_offset=None,
                    reference_base=before[i],
                    observed_base=None,
                )
            )
            i += 1
        else:
            columns.append(
                SequenceComparisonColumn(
                    kind="added",
                    reference_offset=None,
                    observed_offset=j,
                    reference_base=None,
                    observed_base=after[j],
                )
            )
            j += 1
    return SequenceRegionDifference(
        **common,
        correspondence="identical" if before == after else "unique_minimum_edit",
        columns=tuple(columns),
    )
