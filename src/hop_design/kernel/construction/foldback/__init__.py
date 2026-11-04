"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/foldback/__init__.py

Enumerates exact foldback construction programs and sequence solutions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator

from hop_design.models.construction import FoldbackTarget, SequenceDomainPartition

from ..sequence_index import assignment_at, candidate_range
from .domains import solve_foldback_sequence_domain
from .programs import FoldbackProgramCandidate, iter_foldback_programs
from .solutions import FoldbackPlacementFailure, FoldbackSequenceSolution


def iter_foldback_program_solutions(
    *,
    payload_sequence: str,
    target: FoldbackTarget,
    program: FoldbackProgramCandidate,
    start: int = 0,
    stop: int | None = None,
    sequence_partition: SequenceDomainPartition | None = None,
) -> Iterator[FoldbackSequenceSolution | FoldbackPlacementFailure]:
    """Enumerate every exact local source for one target and enzyme program."""
    domain = solve_foldback_sequence_domain(
        payload_sequence=payload_sequence, target=target, program=program
    )
    if isinstance(domain, FoldbackPlacementFailure):
        for _ in candidate_range(1, start=start, stop=stop, partition=sequence_partition):
            yield domain
        return
    for rank in candidate_range(
        domain.precursor_cardinality, start=start, stop=stop, partition=sequence_partition
    ):
        assignment = assignment_at(domain.independent_domains, rank)
        yield domain.materialize("".join(assignment))


__all__ = [
    "FoldbackPlacementFailure",
    "FoldbackProgramCandidate",
    "FoldbackSequenceSolution",
    "iter_foldback_program_solutions",
    "iter_foldback_programs",
]
