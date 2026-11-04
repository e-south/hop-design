"""Preferred work runs first without changing the remaining finite relation."""

import json
from itertools import product

import pytest

from hop_design.design.construction.surveys.completion.navigation import CompletionNavigator
from hop_design.design.construction.surveys.completion.scheduling import schedule_followups
from hop_design.design.construction.surveys.coordinates import coordinate_rank
from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.models.construction.surveys.completion import (
    CompletionAttemptCursor,
    CompletionSeekCursor,
    PreferredCompletionGroup,
)


def _preferred_cursor(**overrides):
    return CompletionSeekCursor.model_validate_json(
        json.dumps(
            {
                "schema": "hop.context-group-seek/v8",
                "preferred_groups": [
                    {"geometry": (1, 0, 0, 0, 0, 0), "page": 1, "group": 1, "depth": 1}
                ],
                **overrides,
            }
        )
    )


@pytest.mark.parametrize("node_budget", [1, 20])
@pytest.mark.parametrize("preferred_succeeds", [False, True])
def test_preference_preserves_complete_membership_after_cold_resume(
    node_budget, preferred_succeeds
):
    order = GeometryOrder(((0, 3), *((0,),) * 5))
    sizes = tuple(len(c) for c in order.costs)
    geometries = tuple(product(*(range(n) for n in sizes)))
    preferred = (geometries[1], 1, 1, 0)
    expected = {
        (g, page, group, pair, member)
        for g in geometries
        for page in range(2)
        for group in range(2)
        for pair in range(2)
        for member in range(1 if preferred_succeeds and (g, page, group, pair) == preferred else 3)
    }
    nav = CompletionNavigator(
        order,
        lambda g, depth, after: iter((depth,)) if depth < 2 and after < depth else iter(()),
        lambda g, page: 2,
    )
    cursor, seen = _preferred_cursor(), []
    for _ in range(1000):
        result = nav.scan(cursor, empty_planes=frozenset(), maximum_nodes=node_budget)
        cursor = result.cursor
        if result.address is not None:
            g, page, group = result.address
            work = result.work
            seen.append((g, page, group, work.pair, work.member))
            done = preferred_succeeds and (g, page, group, work.pair) == preferred
            cursor = schedule_followups(
                CompletionAttemptCursor(
                    **work.model_dump(),
                    geometry_rank=coordinate_rank(sizes, g),
                    page=page,
                    group=group,
                    depth=result.depth,
                    after=cursor,
                ),
                order=order,
                recorded_pairs=2,
                next_member=work.member + 1 if not done and work.member < 2 else None,
                exclusions=(),
                maximum_frontier=100,
            )
        if cursor is None:
            break
        cursor = CompletionSeekCursor.model_validate_json(cursor.model_dump_json())
    else:
        pytest.fail("Finite relation did not exhaust")
    assert seen[0] == (*preferred, 0)
    assert seen[1] == (*preferred[:3], 1, 0)
    assert set(seen) == expected
    assert len(seen) == len(expected)


def test_preferred_groups_are_bounded_unique_and_versioned():
    group = {"geometry": (0,) * 6, "page": 0, "group": 0, "depth": 0}
    for invalid in (
        {"preferred_groups": [group, group]},
        {"preferred_groups": [dict(group, group=i) for i in range(17)]},
        {"preferred_next": 2},
        {"schema": "hop.context-group-seek/v7"},
    ):
        with pytest.raises(ValueError):
            _preferred_cursor(**invalid)


def test_out_of_domain_preference_fails_before_visiting_candidates():
    nav = CompletionNavigator(
        GeometryOrder(tuple((0,) for _ in range(6))),
        lambda *args: pytest.fail("Invalid geometry must fail before page traversal"),
        lambda *args: pytest.fail("Invalid geometry must fail before group admission"),
    )
    with pytest.raises(ValueError, match=r"Preferred.*outside"):
        nav.scan(_preferred_cursor(), empty_planes=frozenset(), maximum_nodes=1)


def test_no_preference_preserves_legacy_cursor_bytes():
    assert CompletionSeekCursor().model_dump(mode="json", by_alias=True) == {
        "schema": "hop.context-group-seek/v4",
        "initialized": False,
        "frontier": [],
    }


def test_preferred_cursor_version_does_not_depend_on_diversity_objective(monkeypatch):
    from types import SimpleNamespace

    from hop_design.design.construction.surveys.completion import preferred
    from hop_design.design.construction.surveys.evaluate import LocalReceipts

    group = PreferredCompletionGroup(geometry=(0,) * 6, page=0, group=0, depth=0)
    monkeypatch.setattr(preferred, "preferred_groups_for", lambda *args: (group,))
    branches = SimpleNamespace(
        request=SimpleNamespace(source_context_objective="paired_scaffold_completions")
    )
    result = LocalReceipts.first_address(None, branches, SimpleNamespace(objective=None), 0)
    assert result["completion_seek"]["schema"] == "hop.context-group-seek/v8"
