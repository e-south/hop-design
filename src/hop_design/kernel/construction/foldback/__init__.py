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
from itertools import product

from hop_design.models.construction import FoldbackTarget

from .domains import solve_foldback_sequence_domain
from .programs import FoldbackProgramCandidate, iter_foldback_programs
from .solutions import FoldbackPlacementFailure, FoldbackSequenceSolution


def iter_foldback_program_solutions(
    *,
    payload_sequence: str,
    target: FoldbackTarget,
    program: FoldbackProgramCandidate,
) -> Iterator[FoldbackSequenceSolution | FoldbackPlacementFailure]:
    """Enumerate every exact local source for one target and enzyme program."""
    domain = solve_foldback_sequence_domain(
        payload_sequence=payload_sequence, target=target, program=program
    )
    if isinstance(domain, FoldbackPlacementFailure):
        yield domain
        return
    for assignment in product(*domain.independent_domains):
        yield domain.materialize("".join(assignment))


__all__ = [
    "FoldbackPlacementFailure",
    "FoldbackProgramCandidate",
    "FoldbackSequenceSolution",
    "iter_foldback_program_solutions",
    "iter_foldback_programs",
]
