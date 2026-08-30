"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/foldback/programs.py

Enumerates finite foldback enzyme and orientation programs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction import FoldbackTarget
from hop_design.models.construction.foldback import FoldbackCleavageProgramKind
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    RecognitionOrientationSemantics,
)
from hop_design.models.physical import SiteOrientation, Strand


@dataclass(frozen=True, slots=True)
class FoldbackProgramCandidate:
    """One finite enzyme and orientation program before sequence placement."""

    kind: FoldbackCleavageProgramKind
    nick_enzyme: CharacterizedEnzyme
    nick_orientation: SiteOrientation
    terminus_enzyme: CharacterizedEnzyme | None
    terminus_orientation: SiteOrientation | None


def iter_foldback_programs(
    policy: EnzymeProvisioningPolicy,
    *,
    target: FoldbackTarget,
) -> tuple[FoldbackProgramCandidate, ...]:
    """Enumerate single and sequential programs in policy-neutral canonical order."""
    nickases = tuple(
        sorted(
            (
                enzyme
                for enzyme in policy.catalog.enzymes
                if enzyme.enzyme_class is EnzymeClass.NICKASE
                and policy.permits(enzyme.enzyme_id, role=EnzymeRole.FOLDBACK_NICK)
            ),
            key=lambda enzyme: enzyme.enzyme_id,
        )
    )
    terminus_options: list[tuple[CharacterizedEnzyme, SiteOrientation]] = []
    for enzyme in sorted(policy.catalog.enzymes, key=lambda item: item.enzyme_id):
        if not policy.permits(enzyme.enzyme_id, role=EnzymeRole.TERMINUS_DEFINITION):
            continue
        if enzyme.enzyme_class is not EnzymeClass.DUPLEX_RESTRICTION:
            continue
        terminus_options.append((enzyme, SiteOrientation.FORWARD))
        if (
            enzyme.recognition_orientation_semantics
            is RecognitionOrientationSemantics.BOTH_ORIENTATIONS
        ):
            terminus_options.append((enzyme, SiteOrientation.REVERSE))

    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Foldback program enumeration requires one exact nick strand.")
    oriented_nickases = tuple(
        (nickase, orientation)
        for nickase in nickases
        for orientation in (
            (SiteOrientation.FORWARD, SiteOrientation.REVERSE)
            if nickase.recognition_orientation_semantics
            is RecognitionOrientationSemantics.BOTH_ORIENTATIONS
            else (SiteOrientation.FORWARD,)
        )
        if (Strand.TOP if orientation is SiteOrientation.FORWARD else Strand.BOTTOM)
        is target.nick_strand
    )
    programs = [
        FoldbackProgramCandidate(
            kind=FoldbackCleavageProgramKind.SINGLE_CLEAVAGE,
            nick_enzyme=nickase,
            nick_orientation=orientation,
            terminus_enzyme=None,
            terminus_orientation=None,
        )
        for nickase, orientation in oriented_nickases
    ]
    programs.extend(
        FoldbackProgramCandidate(
            kind=FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK,
            nick_enzyme=nickase,
            nick_orientation=nick_orientation,
            terminus_enzyme=terminus,
            terminus_orientation=orientation,
        )
        for nickase, nick_orientation in oriented_nickases
        for terminus, orientation in terminus_options
    )
    return tuple(programs)


__all__ = ["FoldbackProgramCandidate", "iter_foldback_programs"]
