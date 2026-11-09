"""Candidate ordering is checked without sorting or retaining another roster."""

from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder


def navigator(order, candidates):
    return CompletionNavigator(
        order,
        lambda *args: iter(()),
        lambda *args: 0,
        admit_basal=lambda _: True,
        basal_candidates=candidates,
    )


def test_order_validation_stops_at_a_proven_inversion(monkeypatch):
    order = GeometryOrder(((0, 1, 2), (0,), (0,), (0,), (0,), (0,)))
    calls = []
    original = GeometryOrder.cost

    def measured(self, geometry):
        calls.append(geometry)
        return original(self, geometry)

    monkeypatch.setattr(GeometryOrder, "cost", measured)
    candidates = tuple((i, 0, 0, 0, 0, 0) for i in (1, 0, 2))
    with pytest.raises(ValueError, match="unique and cost ordered"):
        navigator(order, candidates)
    assert calls == list(candidates[:2])


def test_order_admission_matches_sorted_unique_oracle_with_cost_ties():
    order = GeometryOrder(((2, 0, 2), (0,), (0,), (0,), (4, 1), (0,)))
    choices = tuple((i, 0, 0, 0, 0, 0) for i in range(3))
    for length in range(5):
        for candidates in product(choices, repeat=length):
            keys = tuple((order.cost(g), g) for g in candidates)
            if keys == tuple(sorted(set(keys))):
                assert navigator(order, candidates).basal_candidates == candidates
            else:
                with pytest.raises(ValueError, match="unique and cost ordered"):
                    navigator(order, candidates)
