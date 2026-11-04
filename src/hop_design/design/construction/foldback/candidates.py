"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/foldback/candidates.py

Excludes foldback programs with actionable sites wholly inside the fixed payload.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from collections.abc import Iterator

from hop_design.kernel.construction.foldback import (
    FoldbackPlacementFailure,
    FoldbackSequenceSolution,
    iter_foldback_program_solutions,
)
from hop_design.models.construction.sequence_domain import SequenceDomainPartition
from hop_design.models.physical import Strand
from hop_design.models.reaction_replay import scan_actionable_sites
from hop_design.models.reactions import ReactionMolecule, ReactionState
from hop_design.models.sequence import reverse_complement_iupac

from .traversal import FoldbackWorkUnit


def _payload_has_actionable_site(unit: FoldbackWorkUnit) -> bool:
    sequence = (
        unit.payload_sequence
        if unit.target.nick_strand is Strand.TOP
        else reverse_complement_iupac(unit.payload_sequence)
    )
    state = ReactionState(
        state_id="fixed-payload",
        molecules=(
            ReactionMolecule(
                molecule_id="payload",
                reference_sequence_5prime=sequence,
                complement_sequence_5prime=reverse_complement_iupac(sequence),
            ),
        ),
    )
    return any(
        scan_actionable_sites(state=state, enzyme=enzyme)
        for enzyme in (unit.program.nick_enzyme, unit.program.terminus_enzyme)
        if enzyme is not None
    )


def iter_foldback_candidates(
    unit: FoldbackWorkUnit,
    *,
    sequence_partition: SequenceDomainPartition | None = None,
) -> Iterator[FoldbackSequenceSolution | FoldbackPlacementFailure]:
    """Preserve placement failures and prune a program with an immutable extra site."""
    solutions = iter_foldback_program_solutions(
        payload_sequence=unit.payload_sequence,
        target=unit.target,
        program=unit.program,
        sequence_partition=sequence_partition,
    )
    first = next(solutions, None)
    if first is None:
        return
    if not isinstance(first, FoldbackPlacementFailure) and _payload_has_actionable_site(unit):
        if sequence_partition is None or sequence_partition.part_index == 0:
            yield FoldbackPlacementFailure(code="unintended-actionable-site")
        return
    yield first
    yield from solutions
