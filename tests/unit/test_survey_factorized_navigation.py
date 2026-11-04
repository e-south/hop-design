"""Basal admission precedes the foldback product without deleting alternatives."""

from collections import Counter
from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import CompletionSeekCursor


@pytest.mark.parametrize("budget", [1, 7, 1000])
def test_factorized_admission_charges_once_per_frame_and_keeps_every_admitted_geometry(budget):
    costs = ((0, 2), (1, 0), (0,), (0,), (4, 0, 2, 0), (0, 1))
    order = GeometryOrder(costs)
    admissions = Counter()
    pages_seen = set()

    def admit(g):
        admissions[(*g[:4], g[5])] += 1
        return g[0] == 1

    def pages(g, depth, after):
        pages_seen.add(g)
        return iter((0,)) if depth == 0 and after < 0 else iter(())

    cursor, actual, nodes = CompletionSeekCursor(), [], 0
    while cursor is not None:
        before = sum(admissions.values())
        nav = CompletionNavigator(order, pages, lambda g, p: 2, admit_basal=admit)
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=budget)
        assert sum(admissions.values()) - before <= result.examined_nodes <= budget
        nodes += result.examined_nodes
        if result.address:
            actual.append(result.address)
        cursor = (
            None
            if result.cursor is None
            else CompletionSeekCursor.model_validate_json(result.cursor.model_dump_json())
        )
    geometries = list(product(*(range(len(f)) for f in costs)))
    expected = [
        (g, 0, k)
        for _, k, g in sorted(
            (order.cost(g) + k, k, g) for g in geometries if g[0] == 1 for k in range(2)
        )
    ]
    assert actual == expected
    assert set(admissions.values()) == {1}
    assert len(admissions) == 8
    assert all(g[0] == 1 for g in pages_seen)
    assert nodes < 200


def test_many_foldbacks_do_not_multiply_rejected_frame_work():
    count = 0

    def reject(g):
        nonlocal count
        count += 1
        return False

    def forbidden(*args):
        pytest.fail("Rejected basal frame must never be expanded into local pages")

    nav = CompletionNavigator(
        GeometryOrder(((0, 1), (0,), (0,), (0,), tuple(range(10000)), (0,))),
        forbidden,
        forbidden,
        admit_basal=reject,
    )
    result = nav.scan(CompletionSeekCursor(), empty_planes=frozenset(), maximum_nodes=10)
    assert result.cursor is None
    assert result.address is None
    assert count == 2
    assert result.examined_nodes <= 4


def test_factorized_admission_error_is_not_an_empty_result():
    def unknown(g):
        raise RuntimeError("sequence-space resource limit")

    nav = CompletionNavigator(
        GeometryOrder(((0,),) * 6), lambda *args: iter(()), lambda *args: 0, admit_basal=unknown
    )
    cursor = CompletionSeekCursor()
    with pytest.raises(RuntimeError, match="resource limit"):
        nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=10)
    assert cursor == CompletionSeekCursor()


def test_factorized_frontier_limit_preserves_input_and_resume_path():
    from hop_design.design.construction.surveys.completion.navigation import (
        CompletionFrontierLimitError,
    )

    nav = CompletionNavigator(
        GeometryOrder(((0, 1), (0,), (0,), (0,), (0, 1), (0,))),
        lambda g, d, p: iter((0,)) if d == 0 and p < 0 else iter(()),
        lambda *args: 1,
        admit_basal=lambda g: True,
    )
    cursor = CompletionSeekCursor()
    with pytest.raises(CompletionFrontierLimitError):
        nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=100, maximum_frontier=1)
    assert cursor == CompletionSeekCursor()
    result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=100)
    assert result.address == ((0,) * 6, 0, 0)


def test_new_empty_plane_removes_pending_foldback_expansion():
    nav = CompletionNavigator(
        GeometryOrder(((0,),) * 4 + ((0, 1, 2), (0,))),
        lambda g, d, p: iter((0,)) if d == 0 and p < 0 else iter(()),
        lambda *args: 1,
        admit_basal=lambda g: True,
    )
    first = nav.scan(CompletionSeekCursor(), empty_planes=frozenset(), maximum_nodes=20)
    assert first.address == ((0,) * 6, 0, 0)
    rest = nav.scan(first.cursor, empty_planes=frozenset({(0,) * 5}), maximum_nodes=20)
    assert rest.cursor is None and rest.address is None


def test_old_cursor_schema_cannot_silently_change_search_order():
    with pytest.raises(ValueError):
        CompletionSeekCursor.model_validate({"schema": "hop.context-group-seek/v3"})
