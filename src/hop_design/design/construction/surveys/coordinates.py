"""Direct addresses in a finite Cartesian grid ordered by total index displacement."""

from functools import lru_cache
from math import comb, prod


@lru_cache(maxsize=4096)
def _cumulative(sizes: tuple[int, ...], total: int) -> int:
    """Count bounded integer vectors with sum <= total by inclusion-exclusion."""
    if total < 0:
        return 0
    dimensions = len(sizes)
    answer = 0
    for mask in range(1 << dimensions):
        remaining = total - sum(size for i, size in enumerate(sizes) if mask & (1 << i))
        if remaining >= 0:
            answer += (-1 if mask.bit_count() % 2 else 1) * comb(remaining + dimensions, dimensions)
    return answer


def _exact(sizes: tuple[int, ...], total: int) -> int:
    return _cumulative(sizes, total) - _cumulative(sizes, total - 1)


def coordinate_count(sizes: tuple[int, ...], total: int) -> int:
    """Count addresses in a validated grid up to one total-displacement layer."""
    if total >= sum(n - 1 for n in sizes):
        return prod(sizes)
    return _cumulative(sizes, total)


def coordinate_at(sizes: tuple[int, ...], rank: int) -> tuple[int, ...]:
    """Unrank (sum, lexicographic) order without generating previous grid cells."""
    if (
        not sizes
        or len(sizes) > 8
        or any(type(n) is not int or n < 1 for n in sizes)
        or type(rank) is not int
        or not 0 <= rank < prod(sizes)
    ):
        raise ValueError(
            "Coordinate address requires 1-8 positive dimensions and an in-range integer rank."
        )
    low, high = 0, sum(n - 1 for n in sizes)
    while low < high:
        middle = (low + high) // 2
        if rank < _cumulative(sizes, middle):
            high = middle
        else:
            low = middle + 1
    total = low
    rank -= _cumulative(sizes, total - 1)
    coordinates = []
    for index, size in enumerate(sizes):
        rest = sizes[index + 1 :]
        low, high = 0, min(size - 1, total)
        while low < high:
            middle = (low + high) // 2
            if rank < _exact((middle + 1, *rest), total):
                high = middle
            else:
                low = middle + 1
        if low:
            rank -= _exact((low, *rest), total)
        coordinates.append(low)
        total -= low
    return tuple(coordinates)


def coordinate_rank(sizes: tuple[int, ...], coordinates: tuple[int, ...]) -> int:
    """Recover a canonical address without enumerating preceding grid cells."""
    if (
        not sizes
        or len(sizes) > 8
        or len(coordinates) != len(sizes)
        or any(type(n) is not int or n < 1 for n in sizes)
        or any(
            type(v) is not int or not 0 <= v < n for v, n in zip(coordinates, sizes, strict=True)
        )
    ):
        raise ValueError("Coordinate rank requires 1-8 positive dimensions and in-range integers.")
    remaining = sum(coordinates)
    rank = _cumulative(sizes, remaining - 1)
    for index, value in enumerate(coordinates):
        if value:
            rank += _exact((value, *sizes[index + 1 :]), remaining)
        remaining -= value
    return rank


def interleaved_at(sizes: tuple[int, ...], rank: int) -> tuple[int, int]:
    """Visit each nonempty population at member 0, then member 1, and so on.

    Seek algebraically rather than traversing potentially enormous sequence sets.
    Empty populations retain their index without acquiring invented members.
    """
    if (
        not sizes
        or any(type(n) is not int or n < 0 for n in sizes)
        or type(rank) is not int
        or not 0 <= rank < sum(sizes)
    ):
        raise ValueError("Population address requires nonnegative sizes and an in-range rank.")
    low, high = 0, max(sizes) - 1
    while low < high:
        middle = (low + high) // 2
        if rank < sum(min(size, middle + 1) for size in sizes):
            high = middle
        else:
            low = middle + 1
    remaining = rank - sum(min(size, low) for size in sizes)
    for index, size in enumerate(sizes):
        if size > low:
            if remaining == 0:
                return index, low
            remaining -= 1
    raise AssertionError("Validated population address lost its member.")


def interleaved_rank(sizes: tuple[int, ...], population: int, member: int) -> int:
    """Invert fair population order without enumerating preceding members."""
    if (
        not sizes
        or any(type(n) is not int or n < 0 for n in sizes)
        or type(population) is not int
        or not 0 <= population < len(sizes)
        or type(member) is not int
        or not 0 <= member < sizes[population]
    ):
        raise ValueError("Population rank requires nonnegative sizes and an admitted member.")
    return sum(min(size, member) for size in sizes) + sum(
        size > member for size in sizes[:population]
    )
