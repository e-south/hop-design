"""Seed-first traversal of a correlated DNA set, without changing its membership."""

from dataclasses import dataclass
from functools import cached_property
from math import comb

from hop_design.models.construction.sequence_sets import (
    BASE_ORDER,
    SequenceSet,
    suffix_cardinalities,
)

from .sequence_sets import SequenceSetLimitError


@dataclass(frozen=True)
class SeededSequenceOrder:
    """Order by Hamming distance to the seed prefix, then exact word.

    Unseeded positions do not contribute distance. This is not a primer-quality
    score. The set retains all correlations and owns canonical member addresses.
    """

    sequences: SequenceSet
    seed: str = ""
    max_states: int = 1_000_000

    def __post_init__(self) -> None:
        if len(self.seed) > self.sequences.length_nt or set(self.seed) - set(BASE_ORDER):
            raise ValueError("The ordering seed must be an exact DNA prefix of bounded length.")
        if type(self.max_states) is not int or not 1 <= self.max_states <= 1_000_000:
            raise ValueError("Seed ordering requires a finite positive state budget.")

    @cached_property
    def _counts(self) -> tuple[int, ...]:
        return suffix_cardinalities(self.sequences.length_nt, self.sequences.decisions)

    def _position(self, identity: int) -> int:
        return (
            self.sequences.length_nt
            if identity < 2
            else self.sequences.decisions[identity - 2].position_nt
        )

    @cached_property
    def _distance_counts(self) -> dict[tuple[int, int, int], int]:
        return {}

    def _branches(self, identity: int, position: int) -> tuple[int, ...]:
        return (
            self.sequences.decisions[identity - 2].branches
            if self._position(identity) == position
            else (identity,) * 4
        )

    def key(self, word: str) -> tuple[int, str]:
        """Comparable key, including for a subset with the same seed."""
        return sum(a != b for a, b in zip(word, self.seed, strict=False)), word

    def _penalty(self, position: int, base: str) -> int:
        return int(position < len(self.seed) and base != self.seed[position])

    def _count(self, identity: int, position: int, distance: int) -> int:
        remaining = max(0, len(self.seed) - position)
        if identity == 0 or not 0 <= distance <= remaining:
            return 0
        if remaining == 0:
            count: int = self._counts[identity] * 4 ** (self._position(identity) - position)
            return count
        if identity == 1:
            count = (
                comb(remaining, distance)
                * 3**distance
                * 4 ** (self.sequences.length_nt - position - remaining)
            )
            return count
        key = identity, position, distance
        if key in self._distance_counts:
            return self._distance_counts[key]
        if len(self._distance_counts) >= self.max_states:
            raise SequenceSetLimitError("Seeded context ordering exhausted its state budget.")
        total = sum(
            self._count(child, position + 1, distance - self._penalty(position, base))
            for base, child in zip(BASE_ORDER, self._branches(identity, position), strict=True)
        )
        if len(self._distance_counts) >= self.max_states:
            raise SequenceSetLimitError("Seeded context ordering exhausted its state budget.")
        self._distance_counts[key] = total
        return total

    def member_at(self, rank: int) -> str:
        if not self.seed:
            return self.sequences.member_at(rank)
        if type(rank) is not int or not 0 <= rank < self.sequences.cardinality:
            raise ValueError("Seeded member address is outside its exact sequence set.")
        distance = 0
        for distance in range(len(self.seed) + 1):
            count = self._count(self.sequences.root, 0, distance)
            if rank < count:
                break
            rank -= count
        current, word = self.sequences.root, []
        for position in range(self.sequences.length_nt):
            branches = self._branches(current, position)
            for base in BASE_ORDER:
                child = branches[BASE_ORDER.index(base)]
                penalty = self._penalty(position, base)
                count = self._count(child, position + 1, distance - penalty)
                if rank < count:
                    word.append(base)
                    current = child
                    distance -= penalty
                    break
                rank -= count
        return "".join(word)

    def rank_of(self, word: str) -> int:
        if not self.seed:
            return self.sequences.rank_of(word)
        if not self.sequences.contains(word):
            raise ValueError("Sequence is not a member of the seeded sequence set.")
        distance = self.key(word)[0]
        rank = sum(self._count(self.sequences.root, 0, d) for d in range(distance))
        current = self.sequences.root
        for position, selected in enumerate(word):
            branches = self._branches(current, position)
            for base in BASE_ORDER:
                child = branches[BASE_ORDER.index(base)]
                penalty = self._penalty(position, base)
                if base == selected:
                    current = child
                    distance -= penalty
                    break
                rank += self._count(child, position + 1, distance - penalty)
        return rank
