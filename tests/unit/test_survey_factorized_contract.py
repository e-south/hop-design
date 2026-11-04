"""Independent finite oracles for conditional geometry introductions."""

from itertools import product
from random import Random

import pytest

from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import (
    CompletionFrontierEntry,
    CompletionSeekCursor,
)


def test_irregular_factor_costs_preserve_admitted_group_order():
    random = Random(4301)
    for _ in range(20):
        costs = tuple(tuple(random.randrange(6) for _ in range(n)) for n in (2, 2, 1, 1, 4, 2))
        geometries = list(product(*(range(len(f)) for f in costs)))
        admitted = {(*g[:4], g[5]) for g in geometries if (g[0] + g[1] + g[5]) % 2 == 0}
        order = GeometryOrder(costs)
        nav = CompletionNavigator(
            order,
            lambda g, d, p: (i for i in range(2) if i > p and i == d),
            lambda g, p: 2 + g[4],
            admit_basal=lambda g, admitted=admitted: (*g[:4], g[5]) in admitted,
        )
        actual, cursor = [], CompletionSeekCursor()
        while cursor is not None:
            result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=3)
            if result.address:
                actual.append(result.address)
            cursor = result.cursor
        expected = sorted(
            (order.cost(g) + p + k, k, g, p)
            for g in geometries
            if (*g[:4], g[5]) in admitted
            for p in range(2)
            for k in range(2 + g[4])
        )
        assert actual == [(g, p, k) for _, k, g, p in expected]


@pytest.mark.parametrize("decision", [None, 0, 1])
def test_admission_cannot_silently_coerce_a_missing_or_numeric_decision(decision):
    nav = CompletionNavigator(
        GeometryOrder(((0,),) * 6),
        lambda *args: iter(()),
        lambda *args: 0,
        admit_basal=lambda g: decision,
    )
    with pytest.raises(ValueError, match="Boolean"):
        nav.scan(CompletionSeekCursor(), empty_planes=frozenset(), maximum_nodes=10)


@pytest.mark.parametrize(
    "entry",
    [
        {"kind": "basal", "wave": 10, "geometry": (0,) * 6},
        {"kind": "foldback", "wave": 5, "geometry": (0,) * 6},
        {"kind": "geometry", "wave": 0, "geometry": (0,) * 6},
    ],
)
def test_tampered_frontier_fails_closed(entry):
    nav = CompletionNavigator(
        GeometryOrder(((0,),) * 6),
        lambda *args: iter(()),
        lambda *args: 0,
        admit_basal=lambda g: True,
    )
    cursor = CompletionSeekCursor(initialized=True, frontier=(CompletionFrontierEntry(**entry),))
    with pytest.raises(ValueError):
        nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=10)
