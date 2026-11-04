"""The merged work frontier preserves finite membership and services hard neighbors."""

from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.navigation import (
    CompletionFrontierLimitError,
    CompletionNavigator,
)
from hop_design.design.construction.surveys.completion.scheduling import schedule_followups
from hop_design.design.construction.surveys.coordinates import coordinate_rank
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import (
    CompletionAttemptCursor,
    CompletionFrontierEntry,
    CompletionSeekCursor,
    CompletionWork,
)


@pytest.mark.parametrize("node_budget", [1, 2, 20])
def test_merged_work_exhausts_exact_finite_relation_after_cold_resume(node_budget):
    order = GeometryOrder(((0, 3), *((0,),) * 5))
    sizes = tuple(len(c) for c in order.costs)
    geometries = list(product(*(range(n) for n in sizes)))
    counts = {
        (g, group, pair): 1 + (g[0] + group + pair) % 4
        for g in geometries
        for group in range(3)
        for pair in range(3)
    }
    expected = {
        (g, group, pair, member)
        for (g, group, pair), count in counts.items()
        for member in range(count)
    }
    nav = CompletionNavigator(
        order, lambda g, d, a: iter((0,)) if d == 0 and a < 0 else iter(()), lambda g, p: 3
    )
    cursor, observed, waves = CompletionSeekCursor(), [], []
    for _ in range(1000):
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=node_budget)
        cursor = result.cursor
        if result.address is not None:
            g, page, group = result.address
            work = result.work
            observed.append((g, group, work.pair, work.member))
            waves.append(order.cost(g) + group + work.pair + work.iteration)
            attempt = CompletionAttemptCursor(
                **work.model_dump(),
                geometry_rank=coordinate_rank(sizes, g),
                page=page,
                group=group,
                depth=result.depth,
                after=cursor,
            )
            following = work.member + 1
            cursor = schedule_followups(
                attempt,
                order=order,
                recorded_pairs=3,
                next_member=following if following < counts[g, group, work.pair] else None,
                exclusions=(),
                maximum_frontier=100,
            )
        if cursor is None:
            break
        cursor = CompletionSeekCursor.model_validate_json(cursor.model_dump_json())
    else:
        pytest.fail("Finite work relation failed to exhaust")
    assert set(observed) == expected
    assert len(observed) == len(expected)
    assert waves == sorted(waves)


def test_unfinished_pair_does_not_hold_the_next_pair_or_group():
    order = GeometryOrder(tuple((0,) for _ in range(6)))
    nav = CompletionNavigator(
        order, lambda g, d, a: iter((0,)) if d == 0 and a < 0 else iter(()), lambda g, p: 2
    )
    cursor, seen = CompletionSeekCursor(), []
    for _ in range(12):
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=100)
        _, page, group = result.address
        work = result.work
        seen.append((group, work.pair, work.member))
        attempt = CompletionAttemptCursor(
            **work.model_dump(),
            geometry_rank=0,
            page=page,
            group=group,
            depth=result.depth,
            after=result.cursor,
        )
        cursor = schedule_followups(
            attempt,
            order=order,
            recorded_pairs=2,
            next_member=work.member + 1 if (group, work.pair) == (0, 0) else None,
            exclusions=(),
            maximum_frontier=100,
        )
    assert {(0, 1, 0), (1, 0, 0), (1, 1, 0)} <= set(seen)
    assert sum(group == pair == 0 for group, pair, _ in seen) > 1


def test_pending_bound_raises_without_mutating_saved_cursor():
    order = GeometryOrder(tuple((0,) for _ in range(6)))
    cursor = CompletionSeekCursor(initialized=True)
    attempt = CompletionAttemptCursor(geometry_rank=0, page=0, group=0, after=cursor)
    with pytest.raises(CompletionFrontierLimitError):
        schedule_followups(
            attempt, order=order, recorded_pairs=2, next_member=1, exclusions=(), maximum_frontier=1
        )
    assert not cursor.frontier
    queued = schedule_followups(
        attempt, order=order, recorded_pairs=2, next_member=1, exclusions=(), maximum_frontier=2
    )
    assert len(queued.frontier) == 2


def test_duplicate_pair_work_is_rejected():
    first = CompletionFrontierEntry(
        kind="work", wave=1, geometry=(0,) * 6, page=0, work=CompletionWork(member=1, iteration=1)
    )
    second = first.model_copy(update={"wave": 2, "work": CompletionWork(member=2, iteration=2)})
    with pytest.raises(ValueError, match="duplicate pending"):
        CompletionSeekCursor(initialized=True, frontier=(first, second))
