"""Preferred work uses the actual visitation depth, including sequence rotations."""

import pytest

from hop_design.design.construction.surveys.completion import page_order
from hop_design.design.construction.surveys.coordinates import coordinate_rank


def test_program_depth_uses_member_position_not_combined_population_rank():
    # Interleaved ranks: f=[p0m0,p1m0,p0m1,p1m1,p1m2], b=[p0m0,p1m0,p0m1,p0m2].
    for fi, fd in enumerate((0, 0, 1, 1, 2)):
        for bi, bd in enumerate((0, 0, 1, 2)):
            page = coordinate_rank((5, 4), (fi, bi))
            assert page_order.program_page_depth((2, 3), (3, 1), page) == fd + bd


def test_rotated_program_depth_uses_the_inverse_of_the_declared_rotation():
    frame = (7, (1, 0, 2, 0, 1, 0))
    # The existing v1 rotation starts p0 at member0, p1 at member1.
    # Canonical rank1 (p1m0) is therefore visited last, at depth2.
    for fi, fd in enumerate((0, 2, 1, 0, 1)):
        for bi, bd in enumerate((0, 0, 1, 2)):
            page = coordinate_rank((5, 4), (fi, bi))
            assert (
                page_order.program_page_depth((2, 3), (3, 1), page, foldback_frame=frame) == fd + bd
            )


@pytest.mark.parametrize("frame", [None, (0, (0,)), (512, (1, 2)), (65535, (2, 3, 4))])
def test_inverse_depth_recovers_every_finite_forward_schedule(frame):
    for depth in range(11):
        for page in page_order.program_pages_at_depth(
            (2, 7), (3, 4), depth, maximum_frontier=100, foldback_frame=frame
        ):
            assert (
                page_order.program_page_depth((2, 7), (3, 4), page, foldback_frame=frame) == depth
            )


def test_large_inverse_never_walks_the_forward_schedule(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("Inverse depth must not enumerate sequence members or pages")

    monkeypatch.setattr(page_order, "program_pages_at_depth", fail)
    page = coordinate_rank((10**12, 10**12), (10**12 - 1, 10**12 - 1))
    assert page_order.program_page_depth((10**12,), (10**12,), page) == 2 * (10**12 - 1)


@pytest.mark.parametrize(
    "foldback,basal,page", [((0,), (2,), 0), ((), (1,), 0), ((2,), (1,), 2), ((2,), (1,), True)]
)
def test_invalid_inverse_input_does_not_become_depth_zero(foldback, basal, page):
    with pytest.raises(ValueError):
        page_order.program_page_depth(foldback, basal, page)
