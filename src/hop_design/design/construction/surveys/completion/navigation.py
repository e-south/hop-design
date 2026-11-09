"""Merge admitted group streams without rescanning empty depth products."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from heapq import heapify, heappop, heappush
from math import prod

from hop_design.models.construction.surveys.completion import (
    CompletionFrontierEntry,
    CompletionSeekCursor,
    CompletionWork,
)

from ..geometry_order import GeometryOrder
from ..navigation.pages import Geometry, Plane
from .geometry import GeometryIntroductions


class CompletionFrontierLimitError(RuntimeError):
    """The frontier cannot fit the computation bound; no exclusion follows."""


@dataclass(frozen=True)
class CompletionSeekResult:
    address: tuple[Geometry, int, int] | None
    cursor: CompletionSeekCursor | None
    examined_nodes: int
    depth: int = 0
    work: CompletionWork = field(default_factory=CompletionWork)


def _entry(**values: object) -> CompletionFrontierEntry:
    return CompletionFrontierEntry.model_validate(values)


@dataclass(frozen=True)
class CompletionNavigator:
    """Merge geometry introductions, local pages and contiguous group streams.

    Order: (geometry cost + page depth + group, group, geometry, page).
    Page depths must be contiguous from zero. Discover each page once, then
    retain its next group; never scan an empty depth/group triangle.
    A group is a completion problem, not a supported construction.
    """

    order: GeometryOrder
    pages_at_depth: Callable[[Geometry, int, int], Iterator[int]]
    group_count: Callable[[Geometry, int], int]
    admit_basal: Callable[[Geometry], bool] | None = None
    class_key: Callable[[Geometry, int | None], tuple[str | None, ...]] | None = None
    basal_candidates: tuple[Geometry, ...] | None = None

    def __post_init__(self) -> None:
        if len(self.order.costs) != 6 or any(
            not f or any(type(c) is not int or c < 0 for c in f) for f in self.order.costs
        ):
            raise ValueError("Completion navigation requires six finite nonnegative factors.")
        if self.basal_candidates is not None:
            if self.admit_basal is None:
                raise ValueError("Indexed geometry requires necessary basal admission.")
            for geometry in self.basal_candidates:
                if (
                    len(geometry) != 6
                    or geometry[4] != 0
                    or any(
                        type(v) is not int or not 0 <= v < n
                        for v, n in zip(geometry, self.sizes, strict=True)
                    )
                ):
                    raise ValueError("Indexed basal geometry lies outside the declared domain.")
            keys = tuple((self.order.cost(g), g) for g in self.basal_candidates)
            if keys != tuple(sorted(set(keys))):
                raise ValueError("Indexed basal geometry must be unique and cost ordered.")

    @property
    def sizes(self) -> tuple[int, ...]:
        return tuple(len(f) for f in self.order.costs)

    def scan(
        self,
        cursor: CompletionSeekCursor,
        *,
        empty_planes: frozenset[Plane],
        maximum_nodes: int,
        maximum_frontier: int = 4096,
    ) -> CompletionSeekResult:
        if type(maximum_nodes) is not int or maximum_nodes < 1:
            raise ValueError("Completion navigation requires a positive node budget.")
        if type(maximum_frontier) is not int or not 1 <= maximum_frontier <= 100_000:
            raise ValueError("Completion frontier bound must be between 1 and 100000 entries.")
        sizes = self.sizes
        introductions = GeometryIntroductions(self.order, self.admit_basal, self.basal_candidates)
        for preferred in cursor.preferred_groups:
            if any(v >= n for v, n in zip(preferred.geometry, sizes, strict=True)):
                raise ValueError("Preferred geometry lies outside the declared domain.")
        for entry in cursor.frontier:
            introductions.validate(entry)
            if any(v >= n for v, n in zip(entry.geometry, sizes, strict=True)):
                raise ValueError("Frontier geometry lies outside the declared domain.")
            if entry.kind not in {"geometry", "basal"} and entry.wave != (
                self.order.cost(entry.geometry)
                + entry.depth
                + entry.group
                + (0 if entry.work is None else entry.work.pair + entry.work.iteration)
            ):
                raise ValueError("Frontier wave disagrees with its exact stream coordinates.")
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
            return CompletionSeekResult(None, None, 0)
        if len(cursor.frontier) > maximum_frontier:
            raise CompletionFrontierLimitError("Saved completion frontier exceeds its bound.")
        observed = frozenset(cursor.observed_classes)

        def priority(
            entry: CompletionFrontierEntry,
        ) -> tuple[int, tuple[int, int], int, Geometry, int, int, int, int]:
            # Fairness wave remains first. Within it, complete classes not yet
            # witnessed precede revisits. Introductions stay reachable so an
            # unintroduced class can join this wave; no molecular work is lost.
            keys = (
                self.class_key(entry.geometry, None if entry.kind == "page" else entry.page)
                if self.class_key is not None
                and entry.kind not in {"geometry", "basal", "foldback"}
                else ()
            )
            # A page iterator records its predecessor, not the next candidate.
            # Known structural coordinates can guide it, but its unknown word
            # must not inherit the predecessor's novelty. Each level is ranked
            # separately so a new word cannot hide repeated structure.
            if len(keys) > 2:
                raise ValueError("Allocation supports structural and exact-sequence levels only.")
            covered = (
                int(bool(keys) and keys[0] in observed),
                int(len(keys) > 1 and keys[1] in observed),
            )
            ordinary = entry.priority()
            return ordinary[0], covered, *ordinary[1:]

        heap = [(priority(entry), entry) for entry in cursor.frontier]
        heapify(heap)

        def push(entry: CompletionFrontierEntry) -> None:
            if len(heap) >= maximum_frontier:
                raise CompletionFrontierLimitError("Completion frontier entry bound reached.")
            heappush(heap, (priority(entry), entry))

        def empty() -> CompletionSeekCursor:
            return cursor.model_copy(update={"initialized": True, "frontier": ()})

        def saved() -> CompletionSeekCursor | None:
            return (
                cursor.model_copy(
                    update={
                        "initialized": True,
                        "frontier": tuple(sorted((e for _, e in heap), key=lambda e: e.priority())),
                    }
                )
                if heap
                else None
            )

        if not cursor.initialized:
            initial = introductions.first
            if initial is not None:
                push(initial)
        if cursor.preferred_next < len(cursor.preferred_groups):
            preferred = cursor.preferred_groups[cursor.preferred_next]
            geometry = preferred.geometry
            if (
                (*geometry[:4], geometry[5]) in empty_planes
                or preferred.group >= self.group_count(geometry, preferred.page)
                or (self.admit_basal is not None and not self.admit_basal(geometry))
            ):
                raise ValueError("Preferred group lies outside the admitted domain.")
            after = saved() or empty()
            after = after.model_copy(update={"preferred_next": cursor.preferred_next + 1})
            return CompletionSeekResult(preferred.address, after, 1, preferred.depth)
        preferred_addresses = frozenset(group.address for group in cursor.preferred_groups)
        initial_pairs = [
            (key, entry)
            for key, entry in heap
            if entry.work is not None
            and entry.work.iteration == 0
            and (entry.geometry, entry.page, entry.group) in preferred_addresses
        ]
        if initial_pairs:
            first = min(initial_pairs, key=lambda item: item[0])
            heap.remove(first)
            heapify(heap)
            entry = first[1]
            assert entry.work is not None
            return CompletionSeekResult(
                (entry.geometry, entry.page, entry.group),
                saved() or empty(),
                1,
                entry.depth,
                entry.work,
            )
        examined = 0
        while heap and examined < maximum_nodes:
            _, entry = heappop(heap)
            examined += 1
            geometry = entry.geometry
            if entry.kind in {"geometry", "basal", "foldback"}:
                for following in introductions.advance(entry, empty_planes):
                    push(following)
            elif (*geometry[:4], geometry[5]) in empty_planes:
                continue
            elif entry.kind == "page":
                page = next(self.pages_at_depth(geometry, entry.depth, entry.page), None)
                if page is None:
                    if entry.page >= 0:
                        push(
                            _entry(
                                kind="page",
                                wave=entry.wave + 1,
                                geometry=geometry,
                                depth=entry.depth + 1,
                            )
                        )
                    continue
                if type(page) is not int or page <= entry.page:
                    raise ValueError("A page stream must advance its exact canonical address.")
                count = self.group_count(geometry, page)
                if type(count) is not int or count < 0:
                    raise ValueError("Admitted group count must be a nonnegative integer.")
                push(
                    _entry(
                        kind="page",
                        wave=entry.wave,
                        geometry=geometry,
                        depth=entry.depth,
                        page=page,
                    )
                )
                if count == 0:
                    continue  # Exact domain conditioning proved this page empty.
                push(
                    _entry(
                        kind="group",
                        wave=entry.wave,
                        geometry=geometry,
                        depth=entry.depth,
                        page=page,
                        groups=count,
                    )
                )
            elif entry.kind == "group":
                if entry.group + 1 < entry.groups:
                    push(
                        entry.model_copy(update={"wave": entry.wave + 1, "group": entry.group + 1})
                    )
                if (geometry, entry.page, entry.group) in preferred_addresses:
                    # The prefix introduced this group once. Its other pairs
                    # and failed completions already live in the work frontier.
                    continue
                # The final address still requires molecular evaluation. Its
                # continuation is an explicit empty frontier, not a missing
                # cursor that the caller could mistake for no address at all.
                after = saved() or empty()
                return CompletionSeekResult(
                    (geometry, entry.page, entry.group), after, examined, entry.depth
                )
            else:
                assert entry.work is not None
                after = saved() or empty()
                return CompletionSeekResult(
                    (geometry, entry.page, entry.group), after, examined, entry.depth, entry.work
                )
        return CompletionSeekResult(None, saved(), examined)
