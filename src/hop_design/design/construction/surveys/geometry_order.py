"""Finite visitation costs for legal molecular cases, separate from their addresses."""

from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property, lru_cache

from hop_design.models.construction.discovery.placement import EndPlacement
from hop_design.models.construction.targets import FoldbackTarget


def _distances(rows: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
    """Rank distance from the preferred case along each actual molecular variable."""
    if not rows:
        return ()
    ranks = tuple(
        {value: rank for rank, value in enumerate(sorted(set(column)))}
        for column in zip(*rows, strict=True)
    )
    return tuple(
        sum(
            abs(axis[value] - axis[anchor])
            for axis, value, anchor in zip(ranks, row, rows[0], strict=True)
        )
        for row in rows
    )


def placement_costs(placements: tuple[EndPlacement, ...]) -> tuple[int, ...]:
    return _distances(tuple((p.left_bp, p.right_bp) for p in placements))


def foldback_costs(cases: tuple[FoldbackTarget, ...]) -> tuple[int, ...]:
    words = {word: i for i, word in enumerate(sorted({str(t.loop_sequence) for t in cases}))}
    return _distances(
        tuple(
            (
                t.annealing_arm_length_bp,
                t.junction_offset_nt,
                t.loop_length_nt,
                int(t.nick_strand.value == "bottom"),
                words[str(t.loop_sequence)],
            )
            for t in cases
        )
    )


@dataclass(frozen=True)
class GeometryOrder:
    """Lazy traversal of authored cases; never form new joint permissions."""

    costs: tuple[tuple[int, ...], ...]

    @cached_property
    def maximum(self) -> int:
        return sum(max(factor, default=0) for factor in self.costs)

    def cost(self, coordinates: tuple[int, ...]) -> int:
        return sum(factor[index] for factor, index in zip(self.costs, coordinates, strict=True))

    def at_most(
        self, maximum: int, *, start: tuple[int, ...] | None = None
    ) -> Iterator[tuple[int, ...]]:
        """Yield eligible canonical coordinates in lexicographic order, lazily."""

        if start is not None and (
            len(start) != len(self.costs)
            or any(
                type(v) is not int or not 0 <= v < len(factor)
                for v, factor in zip(start, self.costs, strict=True)
            )
        ):
            raise ValueError("Geometry continuation must lie within its declared factors.")
        suffix_minimum = tuple(
            sum(min(factor) for factor in self.costs[i:]) for i in range(len(self.costs) + 1)
        )

        @lru_cache(maxsize=256)
        def eligible(dimension: int, remaining: int) -> tuple[int, ...]:
            return tuple(i for i, cost in enumerate(self.costs[dimension]) if cost <= remaining)

        def visit(prefix: tuple[int, ...], remaining: int) -> Iterator[tuple[int, ...]]:
            dimension = len(prefix)
            if remaining < suffix_minimum[dimension]:
                return
            if start is not None and prefix < start[:dimension]:
                return
            if dimension == len(self.costs):
                yield prefix
                return
            for index in eligible(dimension, remaining):
                yield from visit((*prefix, index), remaining - self.costs[dimension][index])

        if maximum >= 0:
            yield from visit((), maximum)
