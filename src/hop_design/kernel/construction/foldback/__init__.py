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
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackEnzymeBinding,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeClass,
    EnzymeRole,
)
from hop_design.models.physical import SiteOrientation, Strand
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

from .orientation import mirror_solution, opposite_orientation
from .programs import FoldbackProgramCandidate, iter_foldback_programs
from .solutions import FoldbackPlacementFailure, FoldbackSequenceSolution

_BASES = ("A", "C", "G", "T")


def _oriented_pattern(enzyme: CharacterizedEnzyme, orientation: SiteOrientation) -> str:
    if orientation is SiteOrientation.FORWARD:
        return enzyme.recognition_pattern
    return reverse_complement_iupac(enzyme.recognition_pattern)


def _oriented_cuts(
    enzyme: CharacterizedEnzyme,
    *,
    orientation: SiteOrientation,
    site_start: int,
) -> tuple[int | None, int | None]:
    if orientation is SiteOrientation.FORWARD:
        reference_offset = enzyme.cut_offset_reference_strand
        complement_offset = enzyme.cut_offset_complement_strand
    elif enzyme.enzyme_class is EnzymeClass.NICKASE:
        reference_offset = None
        complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
    else:
        complement_native = enzyme.cut_offset_complement_strand
        if complement_native is None:
            raise ValueError("Duplex restriction enzymes require both strand cuts.")
        reference_offset = enzyme.recognition_length - complement_native
        complement_offset = enzyme.recognition_length - enzyme.cut_offset_reference_strand
    return (
        site_start + reference_offset if reference_offset is not None else None,
        site_start + complement_offset if complement_offset is not None else None,
    )


def _place_binding(
    enzyme: CharacterizedEnzyme,
    *,
    role: EnzymeRole,
    orientation: SiteOrientation,
    controlled_strand: Strand,
    controlled_boundary: int,
) -> FoldbackEnzymeBinding | None:
    if orientation is SiteOrientation.FORWARD:
        controlled_offset = (
            enzyme.cut_offset_reference_strand
            if controlled_strand is Strand.TOP
            else enzyme.cut_offset_complement_strand
        )
    elif enzyme.enzyme_class is EnzymeClass.NICKASE:
        controlled_offset = (
            None
            if controlled_strand is Strand.TOP
            else enzyme.recognition_length - enzyme.cut_offset_reference_strand
        )
    else:
        complement_native = enzyme.cut_offset_complement_strand
        if complement_native is None:
            return None
        controlled_offset = (
            enzyme.recognition_length - complement_native
            if controlled_strand is Strand.TOP
            else enzyme.recognition_length - enzyme.cut_offset_reference_strand
        )
    if controlled_offset is None:
        return None
    site_start = controlled_boundary - controlled_offset
    reference_cut, complement_cut = _oriented_cuts(
        enzyme,
        orientation=orientation,
        site_start=site_start,
    )
    return FoldbackEnzymeBinding.create(
        enzyme_id=enzyme.enzyme_id,
        role=role,
        strand=controlled_strand,
        recognition_span=Span(
            start=Boundary(offset=site_start),
            end=Boundary(offset=site_start + enzyme.recognition_length),
        ),
        orientation=orientation,
        reference_cut=(Boundary(offset=reference_cut) if reference_cut is not None else None),
        complement_cut=(Boundary(offset=complement_cut) if complement_cut is not None else None),
    )


def iter_foldback_program_solutions(
    *,
    payload_sequence: str,
    target: FoldbackTarget,
    program: FoldbackProgramCandidate,
) -> Iterator[FoldbackSequenceSolution | FoldbackPlacementFailure]:
    """Enumerate every exact local source for one target and enzyme program."""
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Foldback sequence discovery requires one exact nick strand.")
    if target.nick_strand is Strand.BOTTOM:
        if program.nick_orientation is not SiteOrientation.REVERSE:
            yield FoldbackPlacementFailure(code="foldback-nick-orientation-unavailable")
            return
        mirrored_program = FoldbackProgramCandidate(
            kind=program.kind,
            nick_enzyme=program.nick_enzyme,
            nick_orientation=SiteOrientation.FORWARD,
            terminus_enzyme=program.terminus_enzyme,
            terminus_orientation=(
                opposite_orientation(program.terminus_orientation)
                if program.terminus_orientation is not None
                else None
            ),
        )
        mirrored_target = target.model_copy(update={"nick_strand": Strand.TOP})
        for solution in iter_foldback_program_solutions(
            payload_sequence=payload_sequence,
            target=mirrored_target,
            program=mirrored_program,
        ):
            yield (
                solution
                if isinstance(solution, FoldbackPlacementFailure)
                else mirror_solution(solution)
            )
        return
    if program.nick_orientation is not SiteOrientation.FORWARD:
        yield FoldbackPlacementFailure(code="foldback-nick-orientation-unavailable")
        return
    payload_nt = len(payload_sequence)
    arm_nt = target.annealing_arm_length_bp
    junction = payload_nt
    nick = junction + target.junction_offset_nt
    foldback_nt = 2 * arm_nt + target.loop_length_nt
    terminus = junction + foldback_nt - target.junction_offset_nt

    nick_binding = _place_binding(
        program.nick_enzyme,
        role=EnzymeRole.FOLDBACK_NICK,
        orientation=program.nick_orientation,
        controlled_strand=Strand.TOP,
        controlled_boundary=nick,
    )
    if nick_binding is None:
        yield FoldbackPlacementFailure(code="foldback-nick-orientation-unavailable")
        return
    bindings = [nick_binding]
    if (
        program.kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE
        and nick_binding.recognition_span.end.offset > terminus
    ):
        yield FoldbackPlacementFailure(code="single-cleavage-site-exceeds-source-terminus")
        return
    if program.terminus_enzyme is not None:
        if program.terminus_orientation is None:
            raise ValueError("A sequential foldback program requires a terminus orientation.")
        terminus_binding = _place_binding(
            program.terminus_enzyme,
            role=EnzymeRole.TERMINUS_DEFINITION,
            orientation=program.terminus_orientation,
            controlled_strand=Strand.BOTTOM,
            controlled_boundary=terminus,
        )
        if terminus_binding is None:
            yield FoldbackPlacementFailure(code="terminus-orientation-unavailable")
            return
        if terminus_binding.reference_cut != Boundary(
            offset=terminus
        ) or terminus_binding.complement_cut != Boundary(offset=terminus):
            yield FoldbackPlacementFailure(code="unsupported-staggered-terminus")
            return
        bindings.append(terminus_binding)

    if any(binding.recognition_span.start.offset < payload_nt for binding in bindings):
        yield FoldbackPlacementFailure(code="payload-recognition-conflict")
        return
    source_nt = max(
        terminus,
        *(binding.recognition_span.end.offset for binding in bindings),
        *(
            cut.offset
            for binding in bindings
            for cut in (binding.reference_cut, binding.complement_cut)
            if cut is not None
        ),
    )
    if (
        program.kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
        and source_nt == terminus
    ):
        yield FoldbackPlacementFailure(code="terminus-cleavage-at-source-end")
        return
    domains = [set(_BASES) for _ in range(source_nt)]
    for coordinate, base in enumerate(payload_sequence):
        domains[coordinate] &= {base}
    for binding in bindings:
        enzyme = (
            program.nick_enzyme
            if binding.role is EnzymeRole.FOLDBACK_NICK
            else program.terminus_enzyme
        )
        if enzyme is None:
            raise RuntimeError("A foldback binding lost its enzyme authority.")
        pattern = _oriented_pattern(enzyme, binding.orientation)
        for offset, symbol in enumerate(pattern):
            coordinate = binding.recognition_span.start.offset + offset
            domains[coordinate] &= iupac_bases(symbol)
    if any(not domain for domain in domains):
        yield FoldbackPlacementFailure(code="overlapping-sequence-conflict")
        return
    arm_domain_sets = [set(_BASES) for _ in range(arm_nt)]
    loop_domain_sets = [set(_BASES) for _ in range(target.loop_length_nt)]
    for source_offset in range(foldback_nt - target.junction_offset_nt):
        final_index = foldback_nt - 1 - source_offset
        source_domain = domains[junction + source_offset]
        if final_index < arm_nt:
            arm_domain_sets[final_index] &= {
                base for base in _BASES if reverse_complement_iupac(base) in source_domain
            }
        elif final_index < arm_nt + target.loop_length_nt:
            loop_index = final_index - arm_nt
            loop_domain_sets[loop_index] &= {
                base for base in _BASES if reverse_complement_iupac(base) in source_domain
            }
        else:
            arm_index = foldback_nt - 1 - final_index
            arm_domain_sets[arm_index] &= source_domain
    arm_domains = tuple(
        tuple(base for base in _BASES if base in domain) for domain in arm_domain_sets
    )
    loop_domains = tuple(
        tuple(base for base in _BASES if base in domain) for domain in loop_domain_sets
    )
    if any(not domain for domain in (*arm_domains, *loop_domains)):
        yield FoldbackPlacementFailure(code="foldback-pairing-conflict")
        return
    canonical_source = [next(base for base in _BASES if base in domain) for domain in domains]
    for assignment in product(*arm_domains, *loop_domains):
        source_bases = canonical_source.copy()
        arm = "".join(assignment[:arm_nt])
        loop = "".join(assignment[arm_nt:])
        foldback = arm + loop + reverse_complement_iupac(arm)
        source_bases[junction:terminus] = reverse_complement_iupac(
            foldback[target.junction_offset_nt :]
        )
        if any(base not in domains[coordinate] for coordinate, base in enumerate(source_bases)):
            continue
        source = "".join(source_bases)
        foldback_segment = foldback
        retained_arm = foldback_segment[:arm_nt]
        loop_start = arm_nt
        loop_end = loop_start + target.loop_length_nt
        realized_loop = foldback_segment[loop_start:loop_end]
        realized_arm = foldback_segment[loop_end:]
        if realized_arm != reverse_complement_iupac(retained_arm):
            raise RuntimeError("Foldback source constraints lost literal arm complementarity.")
        yield FoldbackSequenceSolution(
            source_reference_sequence=source,
            retained_sequence=(
                payload_sequence + foldback_segment + reverse_complement_iupac(payload_sequence)
            ),
            loop_sequence=realized_loop,
            foldback_arm_sequence=realized_arm,
            junction_boundary=junction,
            terminus_boundary=terminus,
            enzyme_bindings=tuple(bindings),
        )


__all__ = [
    "FoldbackPlacementFailure",
    "FoldbackProgramCandidate",
    "FoldbackSequenceSolution",
    "iter_foldback_program_solutions",
    "iter_foldback_programs",
]
