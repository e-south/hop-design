"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/foldback_replay/substrates.py

Maps each foldback cleavage substrate to its exact source-duplex interval.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from dataclasses import dataclass

from hop_design.models.construction.foldback import FoldbackCleavageProgramKind
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.physical import Strand


@dataclass(frozen=True, slots=True)
class FoldbackReactionSubstrate:
    """One complementary duplex present before an enzyme stage."""

    state_id: str
    molecule_id: str
    source_span: Span


def foldback_reaction_substrates(
    *,
    source_nt: int,
    program_kind: FoldbackCleavageProgramKind,
    nick_strand: Strand,
    terminus: int,
) -> tuple[FoldbackReactionSubstrate, ...]:
    """Retain both products of terminus cleavage in the subsequent nicking state."""
    if source_nt < 1 or not 0 <= terminus <= source_nt or not isinstance(nick_strand, Strand):
        raise ValueError("Foldback substrates require an exact strand and in-source terminus.")
    source = FoldbackReactionSubstrate(
        state_id="source-duplex",
        molecule_id="source",
        source_span=Span(start=Boundary(offset=0), end=Boundary(offset=source_nt)),
    )
    if program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE:
        return (source,)
    if program_kind is not FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK:
        raise ValueError("Unsupported foldback cleavage program.")
    left = Span(start=Boundary(offset=0), end=Boundary(offset=terminus))
    right = Span(start=Boundary(offset=terminus), end=Boundary(offset=source_nt))
    retained, released = (left, right) if nick_strand is Strand.TOP else (right, left)
    substrates: tuple[FoldbackReactionSubstrate, ...] = (
        source,
        FoldbackReactionSubstrate(
            state_id="terminus-defined-duplexes", molecule_id="source", source_span=retained
        ),
    )
    if released.length.value:
        substrates += (
            FoldbackReactionSubstrate(
                state_id="terminus-defined-duplexes",
                molecule_id="released-duplex",
                source_span=released,
            ),
        )
    return substrates
