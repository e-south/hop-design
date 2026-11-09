"""Recover the next geometry at an exact cost without earlier-wave scans."""

from bisect import bisect_left
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import cached_property

from hop_design.models.construction.surveys.completion import CompletionFrontierEntry

from ..geometry_order import GeometryOrder
from ..navigation.pages import Geometry, _successor


def at_cost(order: GeometryOrder, cost: int, start: Geometry) -> Iterator[Geometry]:
    minimum = tuple(sum(min(f) for f in order.costs[i:]) for i in range(len(order.costs) + 1))
    maximum = tuple(sum(max(f) for f in order.costs[i:]) for i in range(len(order.costs) + 1))

    def visit(prefix: Geometry, remaining: int) -> Iterator[Geometry]:
        dimension = len(prefix)
        if not minimum[dimension] <= remaining <= maximum[dimension]:
            return
        if prefix < start[:dimension]:
            return
        if dimension == len(order.costs):
            yield prefix
            return
        for index, value in enumerate(order.costs[dimension]):
            if minimum[dimension + 1] <= remaining - value <= maximum[dimension + 1]:
                yield from visit((*prefix, index), remaining - value)

    yield from visit((), cost)


@dataclass(frozen=True)
class GeometryIntroductions:
    """Charge one basal decision before introducing its complete foldback stream.

    An unsupported necessary-condition translation must admit the frame. Only
    an established contradiction may reject it. Every admitted frame retains
    every authored foldback case, in the original total-cost ordering.
    """

    order: GeometryOrder
    admit_basal: Callable[[Geometry], bool] | None = None
    basal_candidates: tuple[Geometry, ...] | None = None

    @cached_property
    def candidate_keys(self) -> tuple[tuple[int, Geometry], ...]:
        offset = min(self.order.costs[4])
        return tuple((self.basal_order.cost(g) + offset, g) for g in self.basal_candidates or ())

    @cached_property
    def basal_order(self) -> GeometryOrder:
        return GeometryOrder((*self.order.costs[:4], (0,), self.order.costs[5]))

    @cached_property
    def foldbacks(self) -> tuple[int, ...]:
        costs = self.order.costs[4]
        return tuple(sorted(range(len(costs)), key=lambda i: (costs[i], i)))

    @cached_property
    def following_foldback(self) -> dict[int, int]:
        return dict(zip(self.foldbacks[:-1], self.foldbacks[1:], strict=True))

    @property
    def first(self) -> CompletionFrontierEntry | None:
        if self.basal_candidates is not None:
            if not self.candidate_keys:
                return None
            wave, geometry = self.candidate_keys[0]
            return CompletionFrontierEntry(kind="basal", wave=wave, geometry=geometry)
        return CompletionFrontierEntry(
            kind="geometry" if self.admit_basal is None else "basal",
            wave=sum(min(f) for f in self.order.costs),
            geometry=(0,) * 6,
        )

    def validate(self, entry: CompletionFrontierEntry) -> None:
        if entry.kind == "geometry" and self.admit_basal is not None:
            raise ValueError("Unfactorized geometry cursor cannot resume factorized search.")
        if entry.kind in {"basal", "foldback"} and self.admit_basal is None:
            raise ValueError("Factorized cursor requires basal admission.")
        if entry.kind == "basal" and entry.geometry[4] != 0:
            raise ValueError("A basal stream cannot bind a foldback case.")
        if entry.kind == "basal" and self.basal_candidates is not None:
            key = (entry.wave, entry.geometry)
            position = bisect_left(self.candidate_keys, key)
            if position == len(self.candidate_keys) or self.candidate_keys[position] != key:
                raise ValueError("Indexed basal cursor differs from its candidate and cost.")
        if entry.kind in {"basal", "geometry"}:
            if not sum(min(f) for f in self.order.costs) <= entry.wave <= self.order.maximum:
                raise ValueError("Geometry stream wave lies outside the declared costs.")
            if entry.kind == "basal" and entry.wave > (
                self.basal_order.maximum + min(self.order.costs[4])
            ):
                raise ValueError("Basal stream wave lies outside the declared costs.")

    def advance(
        self,
        entry: CompletionFrontierEntry,
        empty_planes: frozenset[tuple[int, ...]],
    ) -> Iterator[CompletionFrontierEntry]:
        g = entry.geometry
        if entry.kind == "foldback":
            if (*g[:4], g[5]) in empty_planes:
                return
            next_foldback = self.following_foldback.get(g[4])
            if next_foldback is not None:
                other = (g[0], g[1], g[2], g[3], next_foldback, g[5])
                yield CompletionFrontierEntry(
                    kind="foldback", wave=self.order.cost(other), geometry=other
                )
            yield CompletionFrontierEntry(kind="page", wave=entry.wave, geometry=g)
            return
        factored = entry.kind == "basal"
        order = self.basal_order if factored else self.order
        offset = min(self.order.costs[4]) if factored else 0
        if factored and self.basal_candidates is not None:
            position = bisect_left(self.candidate_keys, (entry.wave, g))
            found = (
                None if position == len(self.candidate_keys) else self.candidate_keys[position][1]
            )
            if position + 1 < len(self.candidate_keys):
                wave, following = self.candidate_keys[position + 1]
                yield entry.model_copy(update={"geometry": following, "wave": wave})
        else:
            found = next(at_cost(order, entry.wave - offset, g), None)
            sizes = tuple(len(f) for f in order.costs)
            following = None if found is None else _successor(found, sizes)
            if following is not None:
                yield entry.model_copy(update={"geometry": following})
            elif entry.wave < order.maximum + offset:
                yield entry.model_copy(update={"wave": entry.wave + 1, "geometry": (0,) * 6})
        if found is None or (*found[:4], found[5]) in empty_planes:
            return
        if not factored:
            yield CompletionFrontierEntry(
                kind="page",
                wave=entry.wave,
                geometry=(found[0], found[1], found[2], found[3], found[4], found[5]),
            )
            return
        assert self.admit_basal is not None
        admitted = self.admit_basal(found)
        if type(admitted) is not bool:
            raise ValueError("Basal admission must be an explicit Boolean decision.")
        if admitted:
            full = (found[0], found[1], found[2], found[3], self.foldbacks[0], found[5])
            yield CompletionFrontierEntry(
                kind="foldback", wave=self.order.cost(full), geometry=full
            )
