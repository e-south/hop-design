"""Finite oracle for pruning complete empty planes without dropping other addresses."""

from itertools import pairwise, product

import pytest

from hop_design.design.construction.surveys.geometry_order import GeometryOrder
from hop_design.design.construction.surveys.navigation import PageNavigator
from hop_design.models.construction.surveys.navigation import SurveySeekCursor

SIZES = (1, 3, 1, 1, 3, 1)
COSTS = ((0,), (0, 1, 2), (0,), (0,), (0, 1, 2), (0,))
EMPTY = frozenset({(0, 1, 0, 0, 0)})


def oracle(contexts=2):
    """Exhaustive tiny grid, independent of the optimized navigation algorithm."""
    geometries = sorted(product(*(range(n) for n in SIZES)), key=lambda g: (sum(g), g))
    rows = []
    for context in range(contexts):
        for rank, geometry in enumerate(geometries):
            pairs = (
                [(0, 0)]
                if geometry[1] == 1
                else sorted(product(range(2), range(1 + geometry[1])), key=lambda p: (sum(p), p))
            )
            for page, pair in enumerate(pairs):
                rows.append(
                    (
                        context + sum(geometry) + sum(pair),
                        context,
                        geometry,
                        page,
                        context * len(geometries) + rank,
                    )
                )
    return sorted(rows)


def navigator(contexts=2):
    calls = []

    def pages(geometry, depth, after):
        calls.append(geometry)
        pairs = (
            [(0, 0)]
            if geometry[1] == 1
            else sorted(product(range(2), range(1 + geometry[1])), key=lambda p: (sum(p), p))
        )
        return (i for i, pair in enumerate(pairs) if sum(pair) == depth and i > after)

    return PageNavigator(GeometryOrder(COSTS), contexts, pages, lambda geometry, page, c: c), calls


@pytest.mark.parametrize("budget", [1, 2, 7, 1000])
def test_certified_planes_preserve_the_complete_nonempty_subsequence_after_cold_resume(budget):
    expected = [(row[4], row[3]) for row in oracle() if row[2][1] != 1]
    engine, calls = navigator()
    cursor, observed, receipts, all_calls = SurveySeekCursor(), [], [], []
    while cursor is not None:
        result = engine.scan(cursor, empty_planes=EMPTY, maximum_nodes=budget)
        assert 0 <= result.examined_nodes <= budget
        if result.address is not None:
            observed.append(result.address)
        cursor = result.cursor
        receipts.append(result)
        if cursor is not None:
            # Every continuation must survive strict serialization and a fresh owner.
            cursor = SurveySeekCursor.model_validate_json(cursor.model_dump_json())
            all_calls.extend(calls)
            engine, calls = navigator()
    assert observed == expected
    all_calls.extend(calls)
    assert all(g[1] != 1 for g in all_calls)
    assert len(observed) == len(set(observed))
    assert all(a.cursor != b.cursor for a, b in pairwise(receipts))


def test_unpruned_order_keeps_the_original_empty_and_nonempty_addresses():
    engine, _ = navigator()
    cursor, observed = SurveySeekCursor(), []
    while cursor is not None:
        result = engine.scan(cursor, empty_planes=frozenset(), maximum_nodes=3)
        if result.address is not None:
            observed.append(result.address)
        cursor = result.cursor
    assert observed == [(row[4], row[3]) for row in oracle()]


def test_all_certified_planes_exhaust_an_enormous_context_domain_without_materialization():
    engine, calls = navigator(10**30)
    all_planes = frozenset((0, nick, 0, 0, 0) for nick in range(3))
    result = engine.scan(SurveySeekCursor(), empty_planes=all_planes, maximum_nodes=1)
    assert result.address is None and result.cursor is None
    assert result.examined_nodes == 0 and calls == []


def test_a_tiny_budget_checkpoints_empty_navigation_instead_of_hiding_an_unbounded_scan():
    calls = []
    engine = PageNavigator(
        GeometryOrder(COSTS),
        10**30,
        lambda g, d, after: calls.append(g) or iter(()),
        lambda g, p, c: c,
    )
    result = engine.scan(SurveySeekCursor(), empty_planes=EMPTY, maximum_nodes=2)
    assert result.address is None and result.cursor is not None
    assert result.examined_nodes == 2
    assert len(calls) <= 2
    resumed = engine.scan(result.cursor, empty_planes=EMPTY, maximum_nodes=2)
    assert resumed.cursor != result.cursor


def test_two_targets_have_independent_certificate_and_cursor_histories():
    left, _ = navigator()
    right, _ = navigator()
    cursors = [SurveySeekCursor(), SurveySeekCursor()]
    results = [[], []]
    for turn in range(2000):
        i = turn % 2
        if cursors[i] is None:
            if all(c is None for c in cursors):
                break
            continue
        value = [left, right][i].scan(
            cursors[i], empty_planes=[EMPTY, frozenset()][i], maximum_nodes=1
        )
        if value.address is not None:
            results[i].append(value.address)
        cursors[i] = value.cursor
    assert all(c is None for c in cursors)
    assert results[0] == [(r[4], r[3]) for r in oracle() if r[2][1] != 1]
    assert results[1] == [(r[4], r[3]) for r in oracle()]


@pytest.mark.parametrize(
    "changes",
    [{"wave": -1}, {"context": -1}, {"page_after": -2}, {"wave": True}, {"unexpected": 0}],
)
def test_seek_cursor_rejects_malformed_continuations(changes):
    with pytest.raises(ValueError):
        SurveySeekCursor.model_validate(changes)


def test_navigation_exhaustion_does_not_upgrade_prior_incomplete_coverage():
    from types import SimpleNamespace

    from hop_design.design.construction.surveys.navigation.advance import navigation_record
    from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits

    order = GeometryOrder(COSTS)
    branches = SimpleNamespace(search_order=lambda limits: order, context_count=10**30)
    all_planes = frozenset((0, nick, 0, 0, 0) for nick in range(3))
    result = navigation_record(
        None,
        branches,
        SurveyEvaluationLimits(local_nodes=1, local_realizations=1, release_site_pairs=1),
        0,
        {
            "seek": SurveySeekCursor().model_dump(mode="json", by_alias=True),
            "exhaustion_proven": False,
        },
        planes=all_planes,
    )
    assert result["next"] is None and result["exhaustion_proven"] is False
    assert result["continuations_examined"] == 0


def test_a_deep_local_diagonal_seeks_after_the_page_without_replaying_earlier_pages():
    from types import SimpleNamespace

    from hop_design.design.construction.surveys.coordinates import coordinate_rank
    from hop_design.design.construction.surveys.partitions import ProductParts

    size = 10**12
    plan = ProductParts(foldback=SimpleNamespace(parts=size), basal=SimpleNamespace(parts=size))
    depth = size - 1
    previous = coordinate_rank((size, size), (size // 2, depth - size // 2))
    expected = coordinate_rank((size, size), (size // 2 + 1, depth - size // 2 - 1))
    yielded = []

    def pages(geometry, requested_depth, after):
        for page in plan.pages_at_depth(requested_depth, after=after):
            yielded.append(page)
            assert len(yielded) == 1, "Revisited an earlier page despite the seek cursor"
            yield page

    engine = PageNavigator(GeometryOrder(((0,),) * 6), 1, pages, lambda g, p, c: c)
    cursor = SurveySeekCursor(
        wave=depth, geometry=(0, 0, 0, 0, 0, 0), page_after=previous, wave_has_page=True
    )
    result = engine.scan(cursor, empty_planes=frozenset(), maximum_nodes=1)
    assert result.address == (0, expected)
    assert result.examined_nodes == 1 and yielded == [expected]


def test_midstream_proofs_with_page_dependent_context_order_do_not_depend_on_target_interleaving():
    geometries = sorted(product(*(range(n) for n in SIZES)), key=lambda g: (sum(g), g))

    def target_rows(target):
        rows = []
        empty_nick = target + 1
        for geometry_rank, geometry in enumerate(geometries):
            pairs = (
                [(0, 0)]
                if geometry[1] == empty_nick
                else sorted(product(range(2), range(1 + geometry[1])), key=lambda p: (sum(p), p))
            )
            for page, pair in enumerate(pairs):
                for position in range(2):
                    context = position ^ ((sum(geometry) + page) % 2)
                    rows.append(
                        (
                            position + sum(geometry) + sum(pair),
                            position,
                            geometry,
                            page,
                            context * len(geometries) + geometry_rank,
                        )
                    )
        return sorted(rows)

    expected = []
    for target in range(2):
        first_empty, kept = True, []
        for row in target_rows(target):
            if row[2][1] == target + 1:
                if not first_empty:
                    continue
                first_empty = False
            kept.append((row[4], row[3]))
        expected.append(kept)

    def execute(interleaved):
        cursors, planes, addresses = (
            [SurveySeekCursor(), SurveySeekCursor()],
            [set(), set()],
            [[], []],
        )
        for turn in range(4000):
            target = turn % 2 if interleaved else (0 if cursors[0] is not None else 1)
            if cursors[target] is None:
                if all(cursor is None for cursor in cursors):
                    break
                continue
            empty_nick = target + 1

            def pages(geometry, depth, after, empty_nick=empty_nick):
                pairs = (
                    [(0, 0)]
                    if geometry[1] == empty_nick
                    else sorted(
                        product(range(2), range(1 + geometry[1])), key=lambda p: (sum(p), p)
                    )
                )
                return (p for p, pair in enumerate(pairs) if sum(pair) == depth and p > after)

            engine = PageNavigator(
                GeometryOrder(COSTS), 2, pages, lambda g, p, c: c ^ ((sum(g) + p) % 2)
            )
            outcome = engine.scan(
                cursors[target], empty_planes=frozenset(planes[target]), maximum_nodes=1
            )
            if outcome.address is not None:
                addresses[target].append(outcome.address)
                geometry = geometries[outcome.address[0] % len(geometries)]
                if geometry[1] == empty_nick:
                    planes[target].add((0, empty_nick, 0, 0, 0))
            cursors[target] = outcome.cursor
        assert all(cursor is None for cursor in cursors)
        return addresses

    assert execute(False) == execute(True) == expected
