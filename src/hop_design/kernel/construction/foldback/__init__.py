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
from dataclasses import dataclass
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
    EnzymeProvisioningPolicy,
    EnzymeRole,
    RecognitionOrientationSemantics,
)
from hop_design.models.physical import SiteOrientation, Strand
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

_BASES = ("A", "C", "G", "T")


@dataclass(frozen=True, slots=True)
class FoldbackProgramCandidate:
    """One finite enzyme and orientation program before sequence placement."""

    kind: FoldbackCleavageProgramKind
    nick_enzyme: CharacterizedEnzyme
    terminus_enzyme: CharacterizedEnzyme | None
    terminus_orientation: SiteOrientation | None


@dataclass(frozen=True, slots=True)
class FoldbackSequenceSolution:
    """One exact source and its intended enzyme bindings."""

    source_reference_sequence: str
    retained_sequence: str
    loop_sequence: str
    foldback_arm_sequence: str
    junction_boundary: int
    terminus_boundary: int
    enzyme_bindings: tuple[FoldbackEnzymeBinding, ...]


@dataclass(frozen=True, slots=True)
class FoldbackPlacementFailure:
    """One stable reason a concrete program cannot realize a geometry."""

    code: str


def iter_foldback_programs(
    policy: EnzymeProvisioningPolicy,
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

    programs = [
        FoldbackProgramCandidate(
            kind=FoldbackCleavageProgramKind.SINGLE_CLEAVAGE,
            nick_enzyme=nickase,
            terminus_enzyme=None,
            terminus_orientation=None,
        )
        for nickase in nickases
    ]
    programs.extend(
        FoldbackProgramCandidate(
            kind=FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK,
            nick_enzyme=nickase,
            terminus_enzyme=terminus,
            terminus_orientation=orientation,
        )
        for nickase in nickases
        for terminus, orientation in terminus_options
    )
    return tuple(programs)


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
    payload_nt = len(payload_sequence)
    arm_nt = target.annealing_arm_length_bp
    junction = payload_nt + target.junction_offset_nt
    foldback_nt = 2 * arm_nt + target.loop_length_nt
    terminus = junction + foldback_nt

    nick_binding = _place_binding(
        program.nick_enzyme,
        role=EnzymeRole.FOLDBACK_NICK,
        orientation=SiteOrientation.FORWARD,
        controlled_strand=Strand.TOP,
        controlled_boundary=junction,
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
    junction_domains = tuple(
        tuple(base for base in _BASES if base in domains[coordinate])
        for coordinate in range(payload_nt, junction)
    )
    arm_domains = tuple(
        tuple(
            base
            for base in _BASES
            if base in domains[junction + index]
            and reverse_complement_iupac(base) in domains[terminus - 1 - index]
        )
        for index in range(arm_nt)
    )
    loop_domains = tuple(
        tuple(
            base
            for base in _BASES
            if reverse_complement_iupac(base)
            in domains[junction + arm_nt + target.loop_length_nt - 1 - index]
        )
        for index in range(target.loop_length_nt)
    )
    if any(not domain for domain in (*arm_domains, *loop_domains)):
        yield FoldbackPlacementFailure(code="foldback-pairing-conflict")
        return
    canonical_source = [next(base for base in _BASES if base in domain) for domain in domains]
    for junction_assignment, arm_assignment, loop_assignment in product(
        product(*junction_domains),
        product(*arm_domains),
        product(*loop_domains),
    ):
        source_bases = canonical_source.copy()
        source_bases[payload_nt:junction] = junction_assignment
        arm = "".join(arm_assignment)
        loop = "".join(loop_assignment)
        foldback = arm + loop + reverse_complement_iupac(arm)
        source_bases[junction:terminus] = reverse_complement_iupac(foldback)
        if any(base not in domains[coordinate] for coordinate, base in enumerate(source_bases)):
            continue
        source = "".join(source_bases)
        foldback_segment = reverse_complement_iupac(source[junction:terminus])
        retained_arm = foldback_segment[:arm_nt]
        loop_start = arm_nt
        loop_end = loop_start + target.loop_length_nt
        realized_loop = foldback_segment[loop_start:loop_end]
        realized_arm = foldback_segment[loop_end:]
        if realized_arm != reverse_complement_iupac(retained_arm):
            raise RuntimeError("Foldback source constraints lost literal arm complementarity.")
        yield FoldbackSequenceSolution(
            source_reference_sequence=source,
            retained_sequence=(payload_sequence + "".join(junction_assignment) + foldback_segment),
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
