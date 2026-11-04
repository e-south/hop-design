"""Search work follows emitted groups rather than empty depth/group products."""

import pytest

from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import CompletionSeekCursor


@pytest.mark.parametrize("groups", [16, 64, 256])
def test_single_page_navigation_work_is_linear_with_cold_resume(groups):
    cursor, seen, nodes, page_calls = CompletionSeekCursor(), [], 0, 0

    def pages(geometry, depth, after):
        nonlocal page_calls
        page_calls += 1
        return iter((0,)) if depth == 0 and after < 0 else iter(())

    while cursor is not None:
        navigator = CompletionNavigator(
            GeometryOrder(tuple((0,) for _ in range(6))),
            pages,
            lambda g, p: groups,
        )
        result = navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)
        nodes += result.examined_nodes
        if result.address is not None:
            assert result.cursor is not None
            seen.append(result.address[2])
        cursor = (
            None
            if result.cursor is None
            else CompletionSeekCursor.model_validate_json(result.cursor.model_dump_json())
        )
    assert seen == list(range(groups))
    assert nodes <= 4 * groups + 16
    assert page_calls <= 4


def test_frontier_storage_stop_is_explicit_and_input_cursor_remains_resumable():
    from hop_design.design.construction.surveys.completion.navigation import (
        CompletionFrontierLimitError,
    )

    cursor = CompletionSeekCursor()
    nav = CompletionNavigator(
        GeometryOrder(tuple((0,) for _ in range(6))),
        lambda g, d, after: iter((0,)) if d == 0 and after < 0 else iter(()),
        lambda g, p: 3,
    )
    with pytest.raises(CompletionFrontierLimitError, match="bound"):
        nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=20, maximum_frontier=1)
    assert cursor == CompletionSeekCursor()
    result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=20, maximum_frontier=2)
    assert result.address == ((0,) * 6, 0, 0)


def test_irregular_costs_and_page_group_extents_match_independent_relation():
    from itertools import product
    from random import Random

    random = Random(191)
    for _ in range(20):
        costs = tuple(
            tuple(random.randrange(7) for _ in range(2 if dimension < 3 else 1))
            for dimension in range(6)
        )
        order = GeometryOrder(costs)
        geometries = tuple(product(*(range(len(factor)) for factor in costs)))
        pages = {
            g: sorted(product(range(1 + g[0]), range(2 + g[1])), key=lambda pair: (sum(pair), pair))
            for g in geometries
        }
        counts = {(g, p): random.randrange(1, 7) for g in geometries for p in range(len(pages[g]))}
        expected = sorted(
            (sum(costs[i][g[i]] for i in range(6)) + sum(pair) + group, group, g, p)
            for g in geometries
            for p, pair in enumerate(pages[g])
            for group in range(counts[g, p])
        )
        nav = CompletionNavigator(
            order,
            lambda g, d, after, pages=pages: (
                p for p, pair in enumerate(pages[g]) if p > after and sum(pair) == d
            ),
            lambda g, p, counts=counts: counts[g, p],
        )
        cursor, observed = CompletionSeekCursor(), []
        while cursor is not None:
            result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=2)
            if result.address is not None:
                observed.append(result.address)
            cursor = (
                None
                if result.cursor is None
                else CompletionSeekCursor.model_validate_json(result.cursor.model_dump_json())
            )
        assert observed == [(g, p, group) for _, group, g, p in expected]


def test_new_empty_plane_proof_removes_already_queued_streams():
    geometries = ((0,) * 6, (1, 0, 0, 0, 0, 0))
    original = [
        (g, 0, group)
        for _, group, g in sorted(
            (g[0] + group, group, g) for g in geometries for group in range(5)
        )
    ]
    nav = CompletionNavigator(
        GeometryOrder(((0, 1), *((0,),) * 5)),
        lambda g, d, after: iter((0,)) if d == 0 and after < 0 else iter(()),
        lambda g, p: 5,
    )
    cursor, observed = CompletionSeekCursor(), []
    empty = frozenset()
    while cursor is not None:
        result = nav.scan(cursor, empty_planes=empty, maximum_nodes=4)
        if result.address is not None:
            observed.append(result.address)
            if len(observed) == 3:
                empty = frozenset({(0, 0, 0, 0, 0)})
        cursor = result.cursor
    assert observed[:3] == original[:3]
    assert observed[3:] == [row for row in original[3:] if row[0][0] != 0]
