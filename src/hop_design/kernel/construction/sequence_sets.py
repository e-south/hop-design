"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/sequence_sets.py

Builds canonical exact DNA sets within explicit decision and computation budgets.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from functools import cache
from typing import Literal

from hop_design.models.construction.sequence_sets import (
    BASE_ORDER,
    MAX_SEQUENCE_DECISIONS,
    MAX_SEQUENCE_VARIABLES,
    SequenceDecision,
    SequenceSet,
    suffix_cardinalities,
)
from hop_design.models.sequence import IUPAC_DNA_ALPHABET, iupac_bases

_Branches = tuple[int, int, int, int]
_Operation = Literal["union", "intersection", "difference"]


class SequenceSetLimitError(RuntimeError):
    """Exact set construction exhausted a declared computational resource."""


class SequenceSetBuilder:
    """Own decision handles for one fixed number of independent DNA bases."""

    def __init__(self, *, length_nt: int, max_nodes: int, max_operations: int) -> None:
        for name, value, ceiling in (
            ("length_nt", length_nt, MAX_SEQUENCE_VARIABLES),
            ("max_nodes", max_nodes, MAX_SEQUENCE_DECISIONS),
            ("max_operations", max_operations, 1_000_000),
        ):
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} must be an integer between 1 and {ceiling}.")
        self.length_nt = length_nt
        self.max_nodes = max_nodes
        self.max_operations = max_operations
        self._decisions: list[tuple[int, _Branches]] = []
        self._intern: dict[tuple[int, _Branches], int] = {}
        self._combined: dict[tuple[_Operation, int, int], int] = {}
        self._operations = 0
        self._exhausted: str | None = None

    def _active(self) -> None:
        if self._exhausted is not None:
            raise SequenceSetLimitError(f"Sequence-set {self._exhausted} budget exhausted.")

    def _spend(self) -> None:
        self._active()
        if self._operations >= self.max_operations:
            self._exhausted = "operation"
            self._active()
        self._operations += 1

    def _node(self, position: int, branches: _Branches) -> int:
        if len(set(branches)) == 1:
            return branches[0]
        key = (position, branches)
        if key not in self._intern:
            if len(self._decisions) >= self.max_nodes:
                self._exhausted = "decision"
                self._active()
            self._intern[key] = len(self._decisions) + 2
            self._decisions.append(key)
        return self._intern[key]

    def _check_root(self, root: int) -> None:
        self._active()
        if type(root) is not int or not 0 <= root < len(self._decisions) + 2:
            raise ValueError("Sequence-set handle is outside this builder.")

    def from_domains(self, domains: Sequence[Collection[str]]) -> int:
        """Form the Cartesian set of exact per-base domains; an empty domain excludes all."""
        self._active()
        if len(domains) != self.length_nt or any(set(d) - set(BASE_ORDER) for d in domains):
            raise ValueError("Sequence-set base domains must match its length and DNA alphabet.")
        current = 1
        for position in reversed(range(self.length_nt)):
            self._spend()
            a, c, g, t = (current if base in domains[position] else 0 for base in BASE_ORDER)
            current = self._node(position, (a, c, g, t))
        return current

    def from_iupac(self, pattern: str) -> int:
        """Form an exact set from an uppercase DNA IUPAC pattern."""
        self._active()
        if not isinstance(pattern, str) or set(pattern) - IUPAC_DNA_ALPHABET:
            raise ValueError("Sequence-set pattern must use the DNA IUPAC alphabet.")
        return self.from_domains(tuple(iupac_bases(base) for base in pattern))

    def import_set(self, sequences: SequenceSet) -> int:
        """Load a validated same-length set into this builder's handle space."""
        self._active()
        if sequences.length_nt != self.length_nt:
            raise ValueError("Imported sequence set must have the same independent length.")
        identities = [0, 1]
        for decision in sequences.decisions:
            self._spend()
            a, c, g, t = (identities[child] for child in decision.branches)
            identities.append(self._node(decision.position_nt, (a, c, g, t)))
        return identities[sequences.root]

    def project_window(self, sequences: SequenceSet, *, start: int, end: int) -> int:
        """Keep exact substrings after existentially removing the surrounding bases."""
        self._active()
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= sequences.length_nt
            or end - start != self.length_nt
        ):
            raise ValueError("Projection window must match the destination sequence length.")

        @cache
        def visit(identity: int) -> int:
            self._spend()
            if identity < 2:
                return identity
            decision = sequences.decisions[identity - 2]
            if decision.position_nt >= end:
                return 1
            a, c, g, t = (visit(child) for child in decision.branches)
            if decision.position_nt < start:
                return self.union(self.union(a, c), self.union(g, t))
            return self._node(decision.position_nt - start, (a, c, g, t))

        return visit(sequences.root)

    def union(self, left: int, right: int) -> int:
        """Admit members present in either exact set, once each."""
        return self._operation("union", left, right)

    def intersection(self, left: int, right: int) -> int:
        """Admit only members present in both exact sets."""
        return self._operation("intersection", left, right)

    def difference(self, left: int, right: int) -> int:
        """Remove every right-hand member from the left-hand set."""
        return self._operation("difference", left, right)

    def _operation(self, operation: _Operation, left: int, right: int) -> int:
        self._check_root(left)
        self._check_root(right)
        return self._combine(operation, left, right)

    def _position(self, root: int) -> int:
        return self.length_nt if root < 2 else self._decisions[root - 2][0]

    def _combine(self, operation: _Operation, left: int, right: int) -> int:
        if operation != "difference" and left > right:
            left, right = right, left
        key = (operation, left, right)
        if key in self._combined:
            return self._combined[key]
        self._spend()
        if left == right:
            result = 0 if operation == "difference" else left
        elif operation == "union" and (left == 0 or left == 1):
            result = right if left == 0 else 1
        elif operation == "intersection" and (left == 0 or left == 1):
            result = 0 if left == 0 else right
        elif operation == "difference" and (left == 0 or right in (0, 1)):
            result = left if right == 0 else 0
        else:
            position = min(self._position(left), self._position(right))
            left_branches = (
                self._decisions[left - 2][1] if self._position(left) == position else (left,) * 4
            )
            right_branches = (
                self._decisions[right - 2][1] if self._position(right) == position else (right,) * 4
            )
            a, c, g, t = (
                self._combine(operation, a, b)
                for a, b in zip(left_branches, right_branches, strict=True)
            )
            result = self._node(position, (a, c, g, t))
        self._combined[key] = result
        return result

    def freeze(self, root: int) -> SequenceSet:
        """Serialize only reachable decisions in deterministic A/C/G/T postorder."""
        self._check_root(root)
        identities = {0: 0, 1: 1}
        decisions: list[SequenceDecision] = []

        def visit(identity: int) -> int:
            if identity not in identities:
                position, children = self._decisions[identity - 2]
                a, c, g, t = (visit(child) for child in children)
                decisions.append(SequenceDecision(position_nt=position, branches=(a, c, g, t)))
                identities[identity] = len(decisions) + 1
            return identities[identity]

        canonical_root = visit(root)
        nodes = tuple(decisions)
        counts = suffix_cardinalities(self.length_nt, nodes)
        position = self.length_nt if canonical_root < 2 else nodes[canonical_root - 2].position_nt
        return SequenceSet(
            length_nt=self.length_nt,
            decisions=nodes,
            root=canonical_root,
            cardinality=counts[canonical_root] * 4**position,
        )
