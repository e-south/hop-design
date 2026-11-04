"""Conditional group navigation agrees with a finite independent exhaustive grid."""

from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import CompletionSeekCursor

COSTS = ((0, 5), (0,), (0,), (0,), (0, 2), (0,))
GEOMETRIES = list(product(*(range(len(c)) for c in COSTS)))


def pairs(g):
    return sorted(product(range(2 + g[0]), range(1 + g[4])), key=lambda x: (sum(x), x))


def count(g, page):
    return 1 + ((g[0] + page) % 4)


def engine():
    return CompletionNavigator(
        GeometryOrder(COSTS),
        lambda g, depth, after: (
            p for p, pair in enumerate(pairs(g)) if p > after and sum(pair) == depth
        ),
        count,
    )


def exhaustive():
    order = GeometryOrder(COSTS)
    rows = []
    for g in GEOMETRIES:
        for page, pair in enumerate(pairs(g)):
            for group in range(count(g, page)):
                rows.append((order.cost(g) + sum(pair) + group, group, g, page))
    return [(g, page, group) for _, group, g, page in sorted(rows)]


@pytest.mark.parametrize("budget", [1, 2, 7, 1000])
def test_group_order_and_exhaustion_match_exhaustive_oracle_after_cold_resume(budget):
    cursor = CompletionSeekCursor()
    observed = []
    for _ in range(10000):
        result = engine().scan(cursor, empty_planes=frozenset(), maximum_nodes=budget)
        assert 0 <= result.examined_nodes <= budget
        if result.address is not None:
            observed.append(result.address)
        if result.cursor is None:
            break
        assert result.cursor != cursor
        cursor = CompletionSeekCursor.model_validate_json(result.cursor.model_dump_json())
    else:
        pytest.fail("Finite group navigation did not exhaust")
    assert observed == exhaustive()


def test_ineligible_group_does_not_skip_another_page_at_the_same_depth():
    # At depth 1, page 1 has one group but page 2 has three groups.
    nav = CompletionNavigator(
        GeometryOrder(tuple((0,) for _ in range(6))),
        lambda g, d, after: (
            p for p, pair in enumerate(pairs((0, 0, 0, 0, 1, 0))) if p > after and sum(pair) == d
        ),
        lambda g, p: 3 if p == 2 else 1,
    )
    cursor, observed = CompletionSeekCursor(), []
    while cursor is not None:
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)
        if result.address:
            observed.append(result.address[1:])
        cursor = result.cursor
    assert (2, 2) in observed
    assert (1, 1) not in observed


def test_navigation_is_independent_of_raw_context_word_cardinality():
    # Eleven group assignments can cover N14--N24 auxiliary domains. There is
    # deliberately no raw-context-count parameter on this navigation seam.
    nav = CompletionNavigator(
        GeometryOrder(tuple((0,) for _ in range(6))),
        lambda g, depth, after: iter((0,)) if depth == 0 and after < 0 else iter(()),
        lambda g, p: 11,
    )
    cursor, seen, nodes = CompletionSeekCursor(), [], 0
    while cursor is not None:
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=10)
        nodes += result.examined_nodes
        if result.address:
            seen.append(result.address[2])
        cursor = result.cursor
    assert seen == list(range(11))
    assert nodes < 400


def test_empty_plane_proof_skips_all_its_groups():
    empty = frozenset({(1, 0, 0, 0, 0)})
    cursor, observed = CompletionSeekCursor(), []
    while cursor is not None:
        result = engine().scan(cursor, empty_planes=empty, maximum_nodes=7)
        if result.address:
            observed.append(result.address)
        cursor = result.cursor
    assert observed == [r for r in exhaustive() if r[0][0] != 1]


@pytest.mark.parametrize("count_", [-1, True])
def test_invalid_group_count_cannot_masquerade_as_exclusion(count_):
    nav = CompletionNavigator(
        GeometryOrder(tuple((0,) for _ in range(6))),
        lambda g, d, after: iter((0,)),
        lambda g, p: count_,
    )
    with pytest.raises(ValueError):
        nav.scan(CompletionSeekCursor(), empty_planes=frozenset(), maximum_nodes=3)


def test_empty_interior_wave_does_not_hide_a_later_geometry():
    assert any(g[0] == 1 for g, _, _ in exhaustive())
    nav = CompletionNavigator(
        GeometryOrder(((0, 100), *((0,),) * 5)),
        lambda g, d, after: iter((0,)) if d == 0 and after < 0 else iter(()),
        lambda g, p: 1,
    )
    cursor, seen = CompletionSeekCursor(), []
    while cursor is not None:
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=200)
        if result.address:
            seen.append(result.address)
        cursor = result.cursor
    assert len(seen) == 2 and seen[-1][0][0] == 1


def test_empty_conditioned_page_advances_without_skipping_later_pages():
    nav = CompletionNavigator(
        GeometryOrder(tuple((0,) for _ in range(6))),
        lambda g, depth, after: (p for p in range(3) if p > after and p == depth),
        lambda g, p: 2 if p == 1 else 0,
    )
    cursor, observed = CompletionSeekCursor(), []
    while cursor is not None:
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)
        if result.address:
            observed.append(result.address[1:])
        cursor = result.cursor
    assert observed == [(1, 0), (1, 1)]
