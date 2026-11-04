"""Visit admitted programs at equal sequence depth, preserving exact page addresses."""

from collections.abc import Iterator
from heapq import merge

from ..coordinates import coordinate_at, coordinate_rank, interleaved_at
from .member_order import (
    RepresentativeFrame,
    foldback_member_position,
    foldback_member_ranks,
    validate_frame,
)
from .navigation import CompletionFrontierLimitError


def _member_ranks(sizes: tuple[int, ...], member: int) -> range:
    start = sum(min(size, member) for size in sizes)
    return range(start, start + sum(size > member for size in sizes))


def program_page_depth(
    foldback: tuple[int, ...],
    basal: tuple[int, ...],
    page: int,
    *,
    foldback_frame: RepresentativeFrame | None = None,
) -> int:
    """Invert the effective program schedule, including its optional member rotation."""
    if not foldback or not basal or any(type(n) is not int or n < 1 for n in (*foldback, *basal)):
        raise ValueError("Program-page depth requires positive program populations.")
    fi, bi = coordinate_at((sum(foldback), sum(basal)), page)
    foldback_depth = (
        interleaved_at(foldback, fi)[1]
        if foldback_frame is None
        else foldback_member_position(foldback, fi, foldback_frame)
    )
    return foldback_depth + interleaved_at(basal, bi)[1]


def program_pages_at_depth(
    foldback: tuple[int, ...],
    basal: tuple[int, ...],
    depth: int,
    *,
    after: int = -1,
    maximum_frontier: int,
    foldback_frame: RepresentativeFrame | None = None,
) -> Iterator[int]:
    """Merge a bounded number of exact-address streams without expanding words.

    Each program's first admitted sequence is at depth zero. Depth measures
    sequence visitation within programs, not their ordinal in the combined roster.
    A foldback frame rotates the starting members while preserving exact addresses.
    A frontier limit stops navigation explicitly; it proves no molecular exclusion.
    """
    if (
        not foldback
        or not basal
        or any(type(n) is not int or n < 1 for n in (*foldback, *basal))
        or type(depth) is not int
        or depth < 0
        or type(after) is not int
        or not -1 <= after < sum(foldback) * sum(basal)
        or type(maximum_frontier) is not int
        or not 1 <= maximum_frontier <= 100_000
    ):
        raise ValueError("Program-page navigation requires positive populations and valid bounds.")
    if foldback_frame is not None:
        validate_frame(foldback_frame)
    sizes = (sum(foldback), sum(basal))

    def row(fi: int, members: range) -> Iterator[int]:
        for bi in members:
            page = coordinate_rank(sizes, (fi, bi))
            if page > after:
                yield page

    streams: list[Iterator[int]] = []
    for fd in range(max(0, depth - max(basal) + 1), min(depth, max(foldback) - 1) + 1):
        members = (
            _member_ranks(foldback, fd)
            if foldback_frame is None
            else foldback_member_ranks(
                foldback, fd, foldback_frame, maximum_items=maximum_frontier - len(streams)
            )
        )
        for fi in members:
            if len(streams) >= maximum_frontier:
                raise CompletionFrontierLimitError("Local program-page frontier bound reached.")
            streams.append(row(fi, _member_ranks(basal, depth - fd)))
    yield from merge(*streams)
