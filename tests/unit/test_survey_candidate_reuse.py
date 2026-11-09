"""Candidate-list reuse stays bounded to one screen and the exact visitation order."""

import pytest

from hop_design.design.construction.surveys.completion import shared_screen
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.sequence_sets import SequenceSet
from tests.unit.test_survey_frame_admission import LIMITS, scope


def screen_and_order():
    branches, _, admission = scope()
    screen = shared_screen.BasalScreen.build(admission)
    assert screen is not None
    return screen, branches.search_order(LIMITS)


def test_repeated_target_does_not_rebuild_candidate_membership_or_sort(monkeypatch):
    screen, order = screen_and_order()
    expected = screen.candidates(0, order)
    monkeypatch.setattr(
        SequenceSet, "contains", lambda *args: pytest.fail("Rebuilt target membership")
    )
    monkeypatch.setattr(
        GeometryOrder, "cost", lambda *args: pytest.fail("Rebuilt candidate cost keys")
    )
    assert screen.candidates(0, order) == expected


def test_changed_order_and_target_keep_their_own_candidates():
    screen, order = screen_and_order()
    changed = GeometryOrder(tuple(tuple(reversed(f)) for f in order.costs))
    for target, ordering in ((0, order), (257, changed), (0, changed), (257, order)):
        word = "".join(screen.admissions.branches.request.targets.pair_at(target))
        expected = sorted(
            (
                *screen.unknown,
                *(g for relation, group in screen.groups if relation.contains(word) for g in group),
            ),
            key=lambda g: (ordering.cost(g), g),
        )
        assert screen.candidates(target, ordering) == tuple(expected)
        assert screen.candidates(target, ordering) == tuple(expected)


def test_candidate_eviction_recomputes_without_changing_answers(monkeypatch):
    monkeypatch.setattr(shared_screen, "MAX_CANDIDATE_LISTS", 2)
    screen, order = screen_and_order()
    expected = {t: screen.candidates(t, order) for t in (0, 1)}
    original, calls = SequenceSet.contains, []

    def measured(self, word):
        calls.append(word)
        return original(self, word)

    monkeypatch.setattr(SequenceSet, "contains", measured)
    assert screen.candidates(0, order) == expected[0]  # Refresh recency.
    assert calls == []
    screen.candidates(257, order)
    calls.clear()
    assert screen.candidates(0, order) == expected[0]
    assert calls == []
    assert screen.candidates(1, order) == expected[1]
    assert len(calls) == len(screen.groups)


@pytest.mark.parametrize("invalid", [True, False, -1, 0.0, 65536])
def test_warm_candidates_still_validate_target_and_dimensions(invalid):
    screen, order = screen_and_order()
    screen.candidates(0, order)
    screen.candidates(1, order)
    with pytest.raises(ValueError, match="target"):
        screen.candidates(invalid, order)
    with pytest.raises(ValueError, match="dimensions"):
        screen.candidates(0, GeometryOrder(((0,),) * 6))


def test_a_new_screen_does_not_inherit_candidate_lists(monkeypatch):
    screen, order = screen_and_order()
    expected = screen.candidates(0, order)
    other = shared_screen.BasalScreen(
        screen.admissions, screen.groups, screen.unknown, screen.digest, screen.frame_count
    )
    original, calls = SequenceSet.contains, []

    def measured(self, word):
        calls.append(word)
        return original(self, word)

    monkeypatch.setattr(SequenceSet, "contains", measured)
    assert other.candidates(0, order) == expected
    assert len(calls) == len(screen.groups)
