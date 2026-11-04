"""Broaden every coarse dimension before consuming one huge row-major block."""

from itertools import product
from math import prod

import pytest

from hop_design.design.construction.surveys.coordinates import coordinate_at


@pytest.mark.parametrize("sizes", [(2, 3), (3, 2, 4), (1, 5, 1), (2, 2, 2, 2, 2, 2)])
def test_coordinate_rank_recovers_literal_sorted_grid_address(sizes):
    from hop_design.design.construction.surveys.coordinates import coordinate_rank

    expected = sorted(product(*(range(n) for n in sizes)), key=lambda row: (sum(row), row))
    assert [coordinate_rank(sizes, row) for row in expected] == list(range(prod(sizes)))


def test_coordinate_rank_seeks_large_grid_and_rejects_noncoordinates():
    from hop_design.design.construction.surveys.coordinates import coordinate_rank

    sizes = (10**18, 10**18)
    assert coordinate_rank(sizes, (10**18 - 1, 10**18 - 1)) == 10**36 - 1
    for row in ((True, 0), (-1, 0), (0,), (10**18, 0)):
        with pytest.raises(ValueError):
            coordinate_rank(sizes, row)


@pytest.mark.parametrize("sizes", [(2, 3, 4), (1, 4, 1, 3), (4,), (2, 2, 2, 2, 2)])
def test_direct_coordinates_equal_total_displacement_then_lexicographic_order(sizes):
    expected = sorted(product(*(range(n) for n in sizes)), key=lambda row: (sum(row), row))
    assert [coordinate_at(sizes, rank) for rank in range(prod(sizes))] == expected


def test_billion_cell_grid_reaches_each_dimension_without_scanning_preceding_rows():
    sizes = (169, 13, 19, 5, 2920)
    first = [coordinate_at(sizes, rank) for rank in range(6)]
    assert first[0] == (0, 0, 0, 0, 0)
    assert {tuple(i for i, value in enumerate(row) if value) for row in first[1:]} == {
        (i,) for i in range(5)
    }
    assert coordinate_at(sizes, prod(sizes) - 1) == tuple(n - 1 for n in sizes)


@pytest.mark.parametrize(
    "sizes,rank", [((), 0), ((0, 2), 0), ((2, True), 0), ((2, 3), -1), ((2, 3), 6), ((2, 3), True)]
)
def test_coordinate_addresses_are_strict(sizes, rank):
    with pytest.raises(ValueError):
        coordinate_at(sizes, rank)


@pytest.mark.parametrize("sizes", [(2, 5, 1), (0, 3, 0, 4), (1,), (0, 0, 2)])
def test_population_order_interleaves_programs_without_dropping_members(sizes):
    from hop_design.design.construction.surveys.coordinates import interleaved_at

    expected = [(i, r) for r in range(max(sizes)) for i, size in enumerate(sizes) if r < size]
    assert [interleaved_at(sizes, rank) for rank in range(sum(sizes))] == expected


def test_population_order_seeks_to_last_member_of_a_huge_unequal_population():
    from hop_design.design.construction.surveys.coordinates import interleaved_at

    sizes = (10**18, 0, 2, 10**18 + 3)
    assert [interleaved_at(sizes, rank) for rank in range(3)] == [(0, 0), (2, 0), (3, 0)]
    assert interleaved_at(sizes, sum(sizes) - 1) == (3, 10**18 + 2)


@pytest.mark.parametrize(
    "sizes,rank", [((), 0), ((0, 0), 0), ((-1, 2), 0), ((2, True), 0), ((1,), 1)]
)
def test_population_addresses_are_strict(sizes, rank):
    from hop_design.design.construction.surveys.coordinates import interleaved_at

    with pytest.raises(ValueError):
        interleaved_at(sizes, rank)
