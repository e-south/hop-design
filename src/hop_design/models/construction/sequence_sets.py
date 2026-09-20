"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/sequence_sets.py

Defines bounded canonical exact DNA sets with cardinality and member recovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from functools import cached_property
from typing import Annotated, Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel

MAX_SEQUENCE_VARIABLES = 256
MAX_SEQUENCE_DECISIONS = 100_000
BASE_ORDER = "ACGT"
_Branch = Annotated[int, Field(ge=0)]


class SequenceSpaceLimits(HopModel):
    """Execution limits, independent of the molecular construction envelope."""

    max_cases: int = Field(ge=1, le=100_000)
    max_programs: int = Field(ge=1, le=100_000)
    max_decisions: int = Field(ge=1, le=100_000)
    max_set_operations: int = Field(ge=1, le=1_000_000)
    max_site_checks: int = Field(ge=1, le=1_000_000)
    max_result_decisions: int = Field(ge=1, le=1_000_000)


class SequenceDecision(HopModel):
    """One independent base position with branches ordered A, C, G, T."""

    position_nt: int = Field(ge=0)
    branches: tuple[_Branch, _Branch, _Branch, _Branch]


def suffix_cardinalities(
    length_nt: int, decisions: tuple[SequenceDecision, ...]
) -> tuple[int, ...]:
    """Count suffixes in a validated child-before-parent decision sequence."""
    counts = [0, 1]
    for decision in decisions:
        total = 0
        for child in decision.branches:
            child_position = length_nt if child < 2 else decisions[child - 2].position_nt
            total += counts[child] * 4 ** (child_position - decision.position_nt - 1)
        counts.append(total)
    return tuple(counts)


class SequenceSet(HopModel):
    """Canonical DNA set; terminals 0 and 1 reject or admit every remaining suffix."""

    schema_version: Literal["hop.sequence-set/v1"] = Field(
        default="hop.sequence-set/v1", alias="schema"
    )
    length_nt: int = Field(ge=1, le=MAX_SEQUENCE_VARIABLES)
    decisions: tuple[SequenceDecision, ...] = Field(max_length=MAX_SEQUENCE_DECISIONS)
    root: int = Field(ge=0)
    cardinality: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_decisions(self) -> SequenceSet:
        if self.root >= len(self.decisions) + 2:
            raise ValueError("Sequence-set root is outside its decisions.")
        seen = set()
        for identity, decision in enumerate(self.decisions, start=2):
            if decision.position_nt >= self.length_nt:
                raise ValueError("Sequence-set decision lies beyond its sequence length.")
            if any(child >= identity for child in decision.branches):
                raise ValueError("Sequence-set branches must reference earlier decisions.")
            if any(
                child >= 2 and self.decisions[child - 2].position_nt <= decision.position_nt
                for child in decision.branches
            ):
                raise ValueError("Sequence-set positions must increase along every branch.")
            key = (decision.position_nt, decision.branches)
            if len(set(decision.branches)) == 1 or key in seen:
                raise ValueError("Sequence-set decisions must be reduced and unique.")
            seen.add(key)
        order = []
        visited: set[int] = set()

        def visit(identity: int) -> None:
            if identity < 2 or identity in visited:
                return
            visited.add(identity)
            for child in self.decisions[identity - 2].branches:
                visit(child)
            order.append(identity)

        visit(self.root)
        if order != list(range(2, len(self.decisions) + 2)):
            raise ValueError("Sequence-set decisions must have canonical reachable postorder.")
        expected = self._suffix_counts[self.root] * 4 ** self._position(self.root)
        if self.cardinality != expected:
            raise ValueError("Sequence-set cardinality differs from its exact decisions.")
        return self

    @cached_property
    def _suffix_counts(self) -> tuple[int, ...]:
        return suffix_cardinalities(self.length_nt, self.decisions)

    def _position(self, identity: int) -> int:
        return self.length_nt if identity < 2 else self.decisions[identity - 2].position_nt

    def contains(self, sequence: str) -> bool:
        """Check one exact uppercase member without enumerating other sequences."""
        if (
            not isinstance(sequence, str)
            or len(sequence) != self.length_nt
            or set(sequence) - set(BASE_ORDER)
        ):
            raise ValueError("Membership requires exact DNA of the sequence-set length.")
        current = self.root
        while current >= 2:
            decision = self.decisions[current - 2]
            current = decision.branches[BASE_ORDER.index(sequence[decision.position_nt])]
        return bool(current)

    def member_at(self, rank: int) -> str:
        """Recover a zero-based lexicographic member without expanding the set."""
        if type(rank) is not int or not 0 <= rank < self.cardinality:
            raise ValueError("Sequence-set member rank is outside its cardinality.")
        sequence = []
        current = self.root
        for position in range(self.length_nt):
            branches = (
                self.decisions[current - 2].branches
                if self._position(current) == position
                else (current,) * 4
            )
            for base, child in zip(BASE_ORDER, branches, strict=True):
                count = self._suffix_counts[child] * 4 ** (self._position(child) - position - 1)
                if rank < count:
                    sequence.append(base)
                    current = child
                    break
                rank -= count
        return "".join(sequence)
