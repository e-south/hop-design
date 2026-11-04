"""Observed complete classes alter priority, never finite molecular membership."""

import pytest

from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import CompletionSeekCursor


def test_missing_classes_are_visited_first_and_all_work_survives_cold_resume():
    keys = ("sha256:" + "a" * 64, "sha256:" + "a" * 64, "sha256:" + "b" * 64)
    order = GeometryOrder(((0, 0, 0), *((0,),) * 5))
    navigator = CompletionNavigator(
        order,
        lambda g, d, a: iter((0,)) if d == 0 and a < 0 else iter(()),
        lambda g, p: 1,
        class_key=lambda g, p: (keys[g[0]],),
    )
    cursor = CompletionSeekCursor(schema="hop.context-group-seek/v7", observed_classes=(keys[0],))
    observed = []
    while cursor is not None:
        result = navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=100)
        if result.address is not None:
            observed.append(result.address[0][0])
        cursor = result.cursor
        if cursor is not None:
            cursor = CompletionSeekCursor.model_validate_json(cursor.model_dump_json())
            assert cursor.observed_classes == (keys[0],)
    assert observed == [2, 0, 1]


def test_completion_followups_preserve_observed_diversity():
    from hop_design.design.construction.surveys.completion.scheduling import schedule_followups
    from hop_design.models.construction.surveys.completion import CompletionAttemptCursor

    seen = ("sha256:" + "a" * 64,)
    after = CompletionSeekCursor(
        schema="hop.context-group-seek/v7", initialized=True, observed_classes=seen
    )
    result = schedule_followups(
        CompletionAttemptCursor(geometry_rank=0, page=0, group=0, after=after),
        order=GeometryOrder(tuple((0,) for _ in range(6))),
        recorded_pairs=2,
        next_member=None,
        exclusions=(),
        maximum_frontier=10,
    )
    assert result.observed_classes == seen


def test_feedback_cannot_reorder_a_later_wave_ahead_of_finite_pending_work():
    keys = ("sha256:" + "a" * 64, "sha256:" + "b" * 64)
    navigator = CompletionNavigator(
        GeometryOrder(((0, 1), *((0,),) * 5)),
        lambda g, d, a: iter((0,)) if d == 0 and a < 0 else iter(()),
        lambda g, p: 1,
        class_key=lambda g, p: (keys[g[0]],),
    )
    cursor = CompletionSeekCursor(schema="hop.context-group-seek/v7", observed_classes=(keys[0],))
    found = []
    while cursor is not None:
        result = navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)
        if result.address is not None:
            found.append(result.address[0][0])
        cursor = result.cursor
    assert found == [0, 1]


def test_feedback_is_explicit_versioned_and_canonical():
    key = "sha256:" + "a" * 64
    assert "observed_classes" not in CompletionSeekCursor().model_dump()
    with pytest.raises(ValueError, match="v7"):
        CompletionSeekCursor(observed_classes=(key,))
    with pytest.raises(ValueError, match="unique"):
        CompletionSeekCursor(schema="hop.context-group-seek/v7", observed_classes=(key, key))
    for version in (5, 6):
        with pytest.raises(ValueError, match="schema"):
            CompletionSeekCursor.model_validate({"schema": f"hop.context-group-seek/v{version}"})


def test_sequence_novelty_depends_on_local_page_without_starving_seen_words():
    known, novel = "sha256:" + "a" * 64, "sha256:" + "b" * 64
    navigator = CompletionNavigator(
        GeometryOrder(((0, 0), *((0,),) * 5)),
        lambda g, d, a: iter((d,)) if d < 2 and a < d else iter(()),
        lambda g, p: 1,
        class_key=lambda g, p: (None if p is None else known if g[0] == p else novel,),
    )
    cursor = CompletionSeekCursor(schema="hop.context-group-seek/v7", observed_classes=(known,))
    found = []
    while cursor is not None:
        result = navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=100)
        if result.address is not None:
            geometry, page, _ = result.address
            found.append((geometry[0], page))
        cursor = result.cursor
        if cursor is not None:
            cursor = CompletionSeekCursor.model_validate_json(cursor.model_dump_json())
    assert found == [(1, 0), (0, 0), (0, 1), (1, 1)]


def test_new_structure_precedes_new_word_then_revisits_survive_cold_resume():
    structure_a, structure_b = "sha256:" + "a" * 64, "sha256:" + "b" * 64
    words = tuple("sha256:" + c * 64 for c in "cde")
    keys = ((structure_a, words[0]), (structure_a, words[1]), (structure_b, words[2]))
    navigator = CompletionNavigator(
        GeometryOrder(((0, 0, 0), *((0,),) * 5)),
        lambda g, d, a: iter((0,)) if d == 0 and a < 0 else iter(()),
        lambda g, p: 1,
        class_key=lambda g, p: keys[g[0]],
    )
    cursor = CompletionSeekCursor(
        schema="hop.context-group-seek/v7", observed_classes=(structure_a, words[0])
    )
    visited = []
    while cursor is not None:
        result = navigator.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)
        if result.address is not None:
            visited.append(result.address[0][0])
        cursor = result.cursor
        if cursor is not None:
            cursor = CompletionSeekCursor.model_validate_json(cursor.model_dump_json())
    assert visited == [2, 1, 0]


def test_unknown_introductions_do_not_delay_first_candidate_until_all_geometries_expand():
    navigator = CompletionNavigator(
        GeometryOrder(((0,) * 1000, *((0,),) * 5)),
        lambda g, d, a: iter((0,)) if d == 0 and a < 0 else iter(()),
        lambda g, p: 1,
        class_key=lambda g, p: ("sha256:" + "a" * 64, "sha256:" + "b" * 64),
    )
    result = navigator.scan(
        CompletionSeekCursor(schema="hop.context-group-seek/v7"),
        empty_planes=frozenset(),
        maximum_nodes=10,
    )
    assert result.address == ((0,) * 6, 0, 0)
