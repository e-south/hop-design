"""Request-wide necessary relations retain unknown frames and exact candidates."""

from itertools import product

import pytest

from hop_design.design.construction.execution.feedback import DiscoveryCancelled
from hop_design.design.construction.surveys.completion import shared_screen
from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import CompletionSeekCursor
from tests.unit.test_survey_frame_admission import LIMITS, scope


def test_shared_screen_matches_each_exact_membership_and_reuses_all_frames(monkeypatch):
    branches, relations, admission = scope()
    screen = shared_screen.BasalScreen.build(admission)
    assert screen is not None
    assert screen.facts["unknown_frames"] == 0
    expected = {}
    for target in (0, 1, 257, 65535):
        expected[target] = {
            (*frame[:4], 0, frame[4])
            for frame in product(*(range(branches.geometry_sizes[i]) for i in (0, 1, 2, 3, 5)))
            if admission.assess(target, (*frame[:4], 0, frame[4])).requested_pair_admitted
        }
    monkeypatch.setattr(relations, "relation", lambda _: pytest.fail("Screen rebuilt a relation"))
    for target, admitted in expected.items():
        assert set(screen.candidates(target, branches.search_order(LIMITS))) == admitted
    assert screen.facts["frames"] == 6


def test_unknown_screen_retains_every_frame_and_never_proves_impossibility(monkeypatch):
    branches, relations, admission = scope()
    monkeypatch.setattr(relations, "relation", lambda _: None)
    screen = shared_screen.BasalScreen.build(admission)
    assert screen.facts["unknown_frames"] == 6
    assert len(screen.candidates(1, branches.search_order(LIMITS))) == 6


def test_screen_limit_does_not_construct_a_truncated_candidate_set(monkeypatch):
    _, relations, admission = scope()
    monkeypatch.setattr(shared_screen, "MAX_SCREEN_FRAMES", 1)
    monkeypatch.setattr(relations, "relation", lambda _: pytest.fail("Oversized screen started"))
    assert shared_screen.BasalScreen.build(admission) is None


def test_interrupted_screen_publishes_no_partial_negative_result():
    _, _, admission = scope()
    with pytest.raises(DiscoveryCancelled):
        shared_screen.BasalScreen.build(admission, should_stop=lambda: True)
    screen = shared_screen.BasalScreen.build(admission)
    assert screen.facts["frames"] == 6


def collect(navigator):
    cursor, addresses, examined = CompletionSeekCursor(), [], 0
    while cursor is not None:
        result = navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=7)
        if result.address is not None:
            addresses.append(result.address)
        examined += result.examined_nodes
        # Model round trip stands in for a cold continuation boundary.
        cursor = (
            None
            if result.cursor is None
            else CompletionSeekCursor.model_validate_json(
                result.cursor.model_dump_json(by_alias=True)
            )
        )
    return addresses, examined


def test_indexed_navigation_keeps_addresses_and_cost_order_without_empty_sweeps():
    order = GeometryOrder((tuple(range(60)), (0,), (0,), (0,), (3, 0, 2), (0,)))
    candidates = ((2, 0, 0, 0, 0, 0), (57, 0, 0, 0, 0, 0))
    arguments = {
        "order": order,
        "pages_at_depth": lambda g, depth, after: iter([0] if depth == 0 and after < 0 else []),
        "group_count": lambda g, p: 2,
        "admit_basal": lambda g: g[0] in {2, 57},
    }
    ordinary = collect(CompletionNavigator(**arguments))
    indexed = collect(CompletionNavigator(**arguments, basal_candidates=candidates))
    assert indexed[0] == ordinary[0] and len(indexed[0]) == 12
    assert indexed[1] < ordinary[1] / 2


def test_empty_index_exhausts_without_visiting_molecular_pages():
    navigator = CompletionNavigator(
        GeometryOrder(((0,),) * 6),
        lambda *args: pytest.fail("An excluded frame reached molecular pages"),
        lambda *args: 0,
        admit_basal=lambda _: False,
        basal_candidates=(),
    )
    assert collect(navigator) == ([], 0)


def test_indexed_cursor_cannot_skip_to_a_different_candidate_or_wave():
    from hop_design.models.construction.surveys.completion import CompletionFrontierEntry

    navigator = CompletionNavigator(
        GeometryOrder(((0, 1, 2), (0,), (0,), (0,), (0,), (0,))),
        lambda *args: iter(()),
        lambda *args: 0,
        admit_basal=lambda _: True,
        basal_candidates=((1, 0, 0, 0, 0, 0),),
    )
    for wave, position in ((0, 0), (0, 1), (2, 1)):
        cursor = CompletionSeekCursor(
            initialized=True,
            frontier=(
                CompletionFrontierEntry(
                    kind="basal", wave=wave, geometry=(position, 0, 0, 0, 0, 0)
                ),
            ),
        )
        with pytest.raises(ValueError, match="Indexed basal cursor"):
            navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)


def test_sequence_resource_stop_keeps_frames_eligible(monkeypatch):
    from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError

    branches, relations, admission = scope()

    def limited(_):
        raise SequenceSetLimitError("Bounded solver stopped")

    monkeypatch.setattr(relations, "relation", limited)
    screen = shared_screen.BasalScreen.build(admission)
    assert screen.facts["unknown_frames"] == 6
    assert len(screen.candidates(0, branches.search_order(LIMITS))) == 6


def test_byte_limit_does_not_publish_a_partial_screen(monkeypatch):
    _, _, admission = scope()
    monkeypatch.setattr(shared_screen, "MAX_SCREEN_BYTES", 0)
    assert shared_screen.BasalScreen.build(admission) is None


@pytest.mark.parametrize(
    "candidates",
    [
        ((1, 0, 0, 0, 0, 0),),
        ((0, 0, 0, 0, 1, 0),),
        ((False, 0, 0, 0, 0, 0),),
        ((0, 0, 0, 0, 0, 0),) * 2,
    ],
)
def test_indexed_navigation_rejects_invalid_or_duplicate_geometry(candidates):
    with pytest.raises(ValueError, match="Indexed basal"):
        CompletionNavigator(
            GeometryOrder(((0,),) * 6),
            lambda *args: iter(()),
            lambda *args: 0,
            admit_basal=lambda _: True,
            basal_candidates=candidates,
        )
