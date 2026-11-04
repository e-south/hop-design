"""Program diversity must not depend on sequence-population ordinal or size."""

import pytest

from hop_design.design.construction.surveys.completion.navigation import (
    CompletionFrontierLimitError,
)
from hop_design.design.construction.surveys.completion.page_order import program_pages_at_depth
from hop_design.design.construction.surveys.coordinates import coordinate_at, interleaved_at


def expected(foldback, basal, depth):
    sizes = (sum(foldback), sum(basal))
    return [
        page
        for page in range(sizes[0] * sizes[1])
        if sum(
            interleaved_at(programs, member)[1]
            for programs, member in zip((foldback, basal), coordinate_at(sizes, page), strict=True)
        )
        == depth
    ]


@pytest.mark.parametrize(
    "foldback,basal", [((2,), (2, 3)), ((1, 4), (3, 2)), ((2, 5, 1), (1, 3, 4))]
)
def test_every_exact_page_occurs_once_and_cold_resume_matches_finite_oracle(foldback, basal):
    seen = []
    for depth in range(max(foldback) + max(basal)):
        oracle = expected(foldback, basal, depth)
        for after in (-1, *oracle):
            actual = list(
                program_pages_at_depth(foldback, basal, depth, after=after, maximum_frontier=100)
            )
            assert actual == [page for page in oracle if page > after]
        seen.extend(oracle)
    assert sorted(seen) == list(range(sum(foldback) * sum(basal)))


def test_first_member_of_each_program_has_equal_depth_without_expanding_huge_domains():
    foldback, basal = (10**12,), (10**12, 10**10)
    pages = list(program_pages_at_depth(foldback, basal, 0, maximum_frontier=2))
    assert [coordinate_at((sum(foldback), sum(basal)), page) for page in pages] == [(0, 0), (0, 1)]


def test_deep_page_merge_obeys_existing_frontier_budget_instead_of_allocating_by_word_count():
    with pytest.raises(CompletionFrontierLimitError, match="program-page"):
        list(program_pages_at_depth((10**12,), (10**12,), 10**9, maximum_frontier=4))


@pytest.mark.parametrize(
    "foldback,basal,depth,after,limit",
    [
        ((), (1,), 0, -1, 4),
        ((0,), (1,), 0, -1, 4),
        ((True,), (1,), 0, -1, 4),
        ((1,), (1,), -1, -1, 4),
        ((1,), (1,), 0, 1, 4),
        ((1,), (1,), 0, -1, 0),
    ],
)
def test_invalid_navigation_input_is_not_an_empty_molecular_result(
    foldback, basal, depth, after, limit
):
    with pytest.raises(ValueError):
        list(program_pages_at_depth(foldback, basal, depth, after=after, maximum_frontier=limit))


@pytest.mark.parametrize("frame", [(0, (0,)), (512, (1, 2)), (65535, (2, 3, 4))])
def test_varied_representatives_preserve_every_page_and_cold_resume(frame):
    foldback, basal = (5, 7), (3, 2)
    seen = []
    for depth in range(max(foldback) + max(basal)):
        options = {"maximum_frontier": 100, "foldback_frame": frame}
        pages = list(program_pages_at_depth(foldback, basal, depth, **options))
        assert pages == sorted(set(pages))
        assert len(pages) == len(expected(foldback, basal, depth))
        for after in pages:
            assert list(program_pages_at_depth(foldback, basal, depth, after=after, **options)) == [
                page for page in pages if page > after
            ]
        seen.extend(pages)
    assert sorted(seen) == list(range(sum(foldback) * sum(basal)))


def test_starting_representatives_vary_by_frame_without_expanding_sequence_domains():
    def first(target):
        return list(
            program_pages_at_depth(
                (10**12,),
                (10**12, 10**10),
                0,
                maximum_frontier=2,
                foldback_frame=(target, (1, 2)),
            )
        )

    starts = [first(target) for target in range(4)]
    assert all(len(pages) == 2 for pages in starts)
    assert len({tuple(pages) for pages in starts}) == 4
    assert first(0) == starts[0]
    with pytest.raises(CompletionFrontierLimitError):
        list(
            program_pages_at_depth(
                (10**12,), (10**12,), 10**9, maximum_frontier=4, foldback_frame=(0, (0,))
            )
        )


@pytest.mark.parametrize("frame", [(-1, (0,)), (True, (0,)), (0, ()), (0, (-1,))])
def test_invalid_representative_frame_fails_before_navigation(frame):
    with pytest.raises(ValueError, match="frame"):
        list(program_pages_at_depth((3,), (2,), 0, maximum_frontier=4, foldback_frame=frame))
