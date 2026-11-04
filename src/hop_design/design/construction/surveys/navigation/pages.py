"""Resume finite molecular coordinates without hidden unbounded lookahead."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from math import prod

from hop_design.models.construction.surveys.navigation import SurveySeekCursor

from ..coordinates import coordinate_rank
from ..geometry_order import GeometryOrder

Geometry = tuple[int, ...]
Plane = tuple[int, int, int, int, int]


@dataclass(frozen=True)
class SeekResult:
    address: tuple[int, int] | None
    cursor: SurveySeekCursor | None
    examined_nodes: int


def _successor(coordinates: Geometry, sizes: tuple[int, ...]) -> Geometry | None:
    for dimension in reversed(range(len(sizes))):
        if coordinates[dimension] + 1 < sizes[dimension]:
            return (
                *coordinates[:dimension],
                coordinates[dimension] + 1,
                *((0,) * (len(sizes) - dimension - 1)),
            )
    return None


def _cursor(**values: object) -> SurveySeekCursor:
    return SurveySeekCursor.model_validate(values)


@dataclass(frozen=True)
class PageNavigator:
    """Visit the original ordered nonempty subsequence after admitted exclusions.

    Empty planes fix placement, nick, association, release method and projection;
    they leave foldback and source context free. This class cannot prove them.
    One node is one candidate geometry or a completed context with no candidate.
    A pending cursor is progress, not molecular exclusion or a construction.
    """

    order: GeometryOrder
    context_count: int
    pages_at_depth: Callable[[Geometry, int, int], Iterator[int]]
    context_rank: Callable[[Geometry, int, int], int]

    def __post_init__(self) -> None:
        if (
            type(self.context_count) is not int
            or self.context_count < 1
            or len(self.order.costs) != 6
            or any(
                not factor or any(type(c) is not int or c < 0 for c in factor)
                for factor in self.order.costs
            )
        ):
            raise ValueError(
                "Navigation requires six finite nonnegative geometry factors and contexts."
            )

    @property
    def sizes(self) -> tuple[int, ...]:
        return tuple(len(factor) for factor in self.order.costs)

    def _advance_context(self, cursor: SurveySeekCursor) -> SurveySeekCursor | None:
        context = cursor.context + 1
        if context < min(cursor.wave + 1, self.context_count):
            return _cursor(wave=cursor.wave, context=context, wave_has_page=cursor.wave_has_page)
        last_introduction = self.order.maximum + self.context_count - 1
        # Every nonempty local Cartesian product has contiguous depths. Once all
        # geometries and contexts have entered, an empty full wave proves exhaustion.
        if cursor.wave >= last_introduction and not cursor.wave_has_page:
            return None
        return _cursor(wave=cursor.wave + 1)

    def scan(
        self, cursor: SurveySeekCursor, *, empty_planes: frozenset[Plane], maximum_nodes: int
    ) -> SeekResult:
        if type(maximum_nodes) is not int or maximum_nodes < 1:
            raise ValueError("Navigation requires a positive integer node budget.")
        sizes = self.sizes
        if cursor.context >= self.context_count:
            raise ValueError("Seek context lies outside the declared domain.")
        if cursor.geometry is not None and any(
            v >= n for v, n in zip(cursor.geometry, sizes, strict=True)
        ):
            raise ValueError("Seek geometry lies outside the declared domain.")
        plane_sizes = (*sizes[:4], sizes[5])
        if any(
            len(p) != 5
            or any(
                type(v) is not int or not 0 <= v < n for v, n in zip(p, plane_sizes, strict=True)
            )
            for p in empty_planes
        ):
            raise ValueError("Empty basal plane lies outside the declared domain.")
        if len(empty_planes) == prod(plane_sizes):
            return SeekResult(None, None, 0)
        pending: SurveySeekCursor | None = cursor
        for examined in range(1, maximum_nodes + 1):
            assert pending is not None
            geometry = next(
                self.order.at_most(pending.wave - pending.context, start=pending.geometry), None
            )
            if geometry is None:
                pending = self._advance_context(pending)
            else:
                plane = (*geometry[:4], geometry[5])
                after = pending.page_after if geometry == pending.geometry else -1
                if plane not in empty_planes:
                    depth = pending.wave - pending.context - self.order.cost(geometry)
                    page = next(self.pages_at_depth(geometry, depth, after), None)
                    if page is not None:
                        context = self.context_rank(geometry, page, pending.context)
                        if type(context) is not int or not 0 <= context < self.context_count:
                            raise ValueError(
                                "Conditioned context rank lies outside the declared domain."
                            )
                        address = (context * prod(sizes) + coordinate_rank(sizes, geometry), page)
                        return SeekResult(
                            address,
                            _cursor(
                                wave=pending.wave,
                                context=pending.context,
                                geometry=geometry,
                                page_after=page,
                                wave_has_page=True,
                            ),
                            examined,
                        )
                following = _successor(geometry, sizes)
                pending = (
                    self._advance_context(pending)
                    if following is None
                    else _cursor(
                        wave=pending.wave,
                        context=pending.context,
                        geometry=following,
                        wave_has_page=pending.wave_has_page,
                    )
                )
            if pending is None:
                return SeekResult(None, None, examined)
        return SeekResult(None, pending, maximum_nodes)
