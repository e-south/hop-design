"""Monotone coverage priorities without rescanning the whole target catalogue."""

import heapq
from collections.abc import Iterable, Mapping

from hop_design.models.construction.surveys.targets import InterfaceTargetDomain


class CoverageSchedule:
    """Advance bounded waves, preferring missing words and pairs within each wave.

    Each diagonal partner band visits every left word with a rotated right word.
    Bands enter in exponentially widening groups, while earlier targets get deeper
    compensating attempts. Linear band introduction would require quadratic work
    before the whole pair roster gets even one attempt. For 256 words on each side,
    widening visits all pairs within 130,816 evaluations if targets remain open.
    The wave is the outer priority: unresolved targets cannot indefinitely postpone
    alternative preparations for supported targets. Every pending address remains.

    Support and evaluation depth only increase. A heap entry can be lazily raised
    when a word gains support; it can never hide a better candidate.
    The queue is disposable and rebuilt from committed outcomes on restart.
    """

    def __init__(
        self,
        domain: InterfaceTargetDomain,
        *,
        last: dict[int, int],
        ended: set[int],
        supported: set[int],
    ):
        self._last = dict(last)
        self._right_count = domain.right_count
        self._band_width = domain.left_count
        self._ranks = [domain.coverage_rank(t) for t in range(domain.pair_count)]
        self._supported = set(supported)
        self._left = {t // self._right_count for t in supported}
        self._right = {t % self._right_count for t in supported}
        self._heap = [(*self._priority(t), t) for t in range(domain.pair_count) if t not in ended]
        heapq.heapify(self._heap)
        self._preferred_next: int | None = None

    def prefer_next(self, target: int) -> None:
        """Service one bounded prefix task, retaining its subsequent ordinary work."""
        if type(target) is not int or not 0 <= target < len(self._ranks):
            raise ValueError("Preferred target lies outside the declared domain.")
        if self._preferred_next is not None:
            raise ValueError("Consume the previous preferred target before setting another.")
        pending = [entry for entry in self._heap if entry[-1] != target]
        if len(pending) == len(self._heap):
            raise ValueError("Preferred target has no pending ordinary work.")
        self._heap = pending
        heapq.heapify(self._heap)
        self._preferred_next = target

    def _priority(self, target: int) -> tuple[int, int, int, int]:
        left, right = divmod(target, self._right_count)
        return (
            self._last.get(target, -1) + 1 + (self._ranks[target] // self._band_width).bit_length(),
            int(left in self._left) + int(right in self._right),
            int(target in self._supported),
            self._ranks[target],
        )

    def pop(self) -> int | None:
        if self._preferred_next is not None:
            target, self._preferred_next = self._preferred_next, None
            return target
        while self._heap:
            *priority, target = heapq.heappop(self._heap)
            current = self._priority(target)
            if tuple(priority) == current:
                return target
            heapq.heappush(self._heap, (*current, target))
        return None

    def update(self, target: int, *, step: int, supported: bool, ended: bool) -> None:
        self._last[target] = step
        if supported:
            self._supported.add(target)
            left, right = divmod(target, self._right_count)
            self._left.add(left)
            self._right.add(right)
        if not ended:
            heapq.heappush(self._heap, (*self._priority(target), target))


class DiscoverySchedule(CoverageSchedule):
    """Reach complete preparations earlier while keeping every finite target reachable.

    Raise pending work's priority key every 64 steps while widening the target
    roster. This is not a hard turn cap: rank ties can extend a turn. Finding a
    preparation advances that target's priority immediately,
    letting new options enter sooner. This changes ordering only: each finite
    target remains reachable and molecular permissions remain untouched.
    """

    def _priority(self, target: int) -> tuple[int, int, int, int]:
        left, right = divmod(target, self._right_count)
        return (
            (self._last.get(target, -1) + 1) // 64
            + (self._ranks[target] + 1).bit_length()
            + int(target in self._supported),
            int(left in self._left) + int(right in self._right),
            int(target in self._supported),
            self._ranks[target],
        )


class DiversitySchedule(CoverageSchedule):
    """Spend a finite quantum on within-target contrasts after finding a witness.

    Support does not force an immediate switch to another end pair. Widening
    still reaches every finite target; this policy never excludes a candidate.
    """

    def _priority(self, target: int) -> tuple[int, int, int, int]:
        return (
            (self._last.get(target, -1) + 1) // 64 + (self._ranks[target] + 1).bit_length(),
            0,
            0,
            self._ranks[target],
        )


class InterfaceDiversitySchedule(DiscoverySchedule):
    """Try constraint-derived end pairs before the ordinary coverage fallback.

    Seeds change traversal rank only. Every unseeded target remains in the same
    finite roster; a seed is neither a complete witness nor an exclusion proof.
    Explicit preparation preferences still take precedence through prefer_next.
    Rebuilding from the same seeds and committed outcomes restores the queue.
    Once a target has a complete witness, shorter turns share effort with other
    interfaces. Unresolved targets retain their original construction allowance.
    """

    _SUPPORTED_QUANTUM = 8

    def __init__(
        self,
        domain: InterfaceTargetDomain,
        *,
        last: dict[int, int],
        ended: set[int],
        supported: set[int],
        preferred: tuple[int, ...],
        candidate_classes: Mapping[int, frozenset[str]] | None = None,
        observed_classes: frozenset[str] = frozenset(),
    ):
        if any(type(t) is not int or not 0 <= t < domain.pair_count for t in preferred) or len(
            set(preferred)
        ) != len(preferred):
            raise ValueError("Preferred targets must be distinct addresses in the target domain.")
        self._candidate_classes = dict(candidate_classes or {})
        if any(
            type(t) is not int or not 0 <= t < domain.pair_count for t in self._candidate_classes
        ):
            raise ValueError("Class suggestions must name targets in the declared domain.")
        self._relevant = frozenset().union(*self._candidate_classes.values())
        self._observed = set(observed_classes & self._relevant)
        super().__init__(domain, last=last, ended=ended, supported=supported)
        head = tuple(dict.fromkeys((*preferred, domain.coverage_ordinal(0))))
        chosen = frozenset(head)
        order = (
            *head,
            *(
                domain.coverage_ordinal(r)
                for r in range(domain.pair_count)
                if domain.coverage_ordinal(r) not in chosen
            ),
        )
        for rank, target in enumerate(order):
            self._ranks[target] = rank
        self._heap = [(*self._priority(t), t) for t in range(domain.pair_count) if t not in ended]
        heapq.heapify(self._heap)

    @property
    def observed_classes(self) -> frozenset[str]:
        return frozenset(self._observed)

    def observe_classes(self, classes: Iterable[str]) -> None:
        """Only committed witnesses count; retain bounded relevant classes only."""
        self._observed.update(self._relevant.intersection(classes))

    def _priority(self, target: int) -> tuple[int, int, int, int]:
        ordinary = super()._priority(target)
        if target in self._supported:
            ordinary = (
                (self._last.get(target, -1) + 1) // self._SUPPORTED_QUANTUM
                + (self._ranks[target] + 1).bit_length()
                + 1,
                *ordinary[1:],
            )
        if not self._candidate_classes:
            return ordinary
        possible = self._candidate_classes.get(target, frozenset())
        covered = int(bool(possible) and possible <= self._observed)
        # Keep the finite fairness wave first. Global class coverage only raises
        # priority keys, so the inherited lazy heap remains valid after feedback.
        # Unknown targets are eligible; suggestions never establish exclusion.
        return ordinary[0], covered, ordinary[2], ordinary[3]
