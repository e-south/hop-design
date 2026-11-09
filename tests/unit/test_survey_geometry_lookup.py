"""Indexed geometry seeks inspect logarithmically many existing candidates."""

from itertools import product

from hop_design.design.construction.surveys.completion.geometry import GeometryIntroductions
from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import CompletionFrontierEntry


def test_candidate_validation_derives_dimension_sizes_once(monkeypatch):
    original = CompletionNavigator.sizes.fget
    calls = []

    def measured(self):
        calls.append(None)
        return original(self)

    monkeypatch.setattr(CompletionNavigator, "sizes", property(measured))
    CompletionNavigator(
        GeometryOrder((tuple(range(256)), (0,), (0,), (0,), (0,), (0,))),
        lambda *args: iter(()),
        lambda *args: 0,
        admit_basal=lambda _: True,
        basal_candidates=tuple((i, 0, 0, 0, 0, 0) for i in range(256)),
    )
    assert len(calls) == 1


def test_resumed_lookup_does_not_rebuild_every_candidate_key(monkeypatch):
    order = GeometryOrder((tuple(range(4096)), (0,), (0,), (0,), (7, 2, 5), (0,)))
    candidates = tuple((i, 0, 0, 0, 0, 0) for i in range(4096))
    calls = []
    original = GeometryOrder.cost

    def measured(self, geometry):
        calls.append(geometry)
        return original(self, geometry)

    monkeypatch.setattr(GeometryOrder, "cost", measured)
    introductions = GeometryIntroductions(order, lambda _: True, candidates)
    entry = CompletionFrontierEntry(kind="basal", wave=2050, geometry=candidates[2048])
    introductions.validate(entry)
    following = tuple(introductions.advance(entry, frozenset()))
    assert following[0].geometry == candidates[2049]
    assert following[1].geometry == (2048, 0, 0, 0, 1, 0)
    assert len(calls) <= 40


def test_indexed_lookup_matches_literal_cost_order_with_ties_and_nonzero_offset():
    order = GeometryOrder(((3, 0, 1), (2, 0), (0,), (0,), (7, 2, 5), (1, 0)))
    candidates = tuple(
        sorted(
            ((*g[:4], 0, g[4]) for g in product(range(3), range(2), range(1), range(1), range(2))),
            key=lambda g: (order.cost(g), g),
        )
    )
    expected = tuple((order.cost(g) - 7 + 2, g) for g in candidates)
    introductions = GeometryIntroductions(order, lambda _: True, candidates)
    assert introductions.first.wave == expected[0][0]
    assert introductions.first.geometry == expected[0][1]
    for position, (wave, geometry) in enumerate(expected):
        entry = CompletionFrontierEntry(kind="basal", wave=wave, geometry=geometry)
        introductions.validate(entry)
        observed = tuple(introductions.advance(entry, frozenset()))
        if position + 1 < len(expected):
            next_wave, next_geometry = expected[position + 1]
            assert observed[0] == CompletionFrontierEntry(
                kind="basal", wave=next_wave, geometry=next_geometry
            )
        else:
            assert len(observed) == 1
        assert observed[-1] == CompletionFrontierEntry(
            kind="foldback", wave=wave, geometry=(*geometry[:4], 1, geometry[5])
        )
    assert GeometryIntroductions(order, lambda _: True, ()).first is None
