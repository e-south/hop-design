"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/foldback/domains.py

Solves independent foldback base domains and correlated exact source materialization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import prod

from hop_design.models.construction import FoldbackTarget
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackEnzymeBinding,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import CharacterizedEnzyme, EnzymeClass, EnzymeRole
from hop_design.models.physical import SiteOrientation, Strand
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

from .orientation import mirror_binding, opposite_orientation
from .programs import FoldbackProgramCandidate
from .solutions import FoldbackPlacementFailure, FoldbackSequenceSolution

_BASES = ("A", "C", "G", "T")


@dataclass(frozen=True, slots=True)
class SequenceVariable:
    """One independent base, optionally complemented in a source expression."""

    index: int
    complemented: bool = False


SequenceExpression = tuple[str | SequenceVariable, ...]


def reverse_complement_expression(expression: SequenceExpression) -> SequenceExpression:
    """Reverse and complement literal and correlated variable positions."""
    return tuple(
        reverse_complement_iupac(base)
        if isinstance(base, str)
        else SequenceVariable(base.index, not base.complemented)
        for base in reversed(expression)
    )


@dataclass(frozen=True, slots=True)
class FoldbackSequenceDomain:
    """Finite independent arm/cap bases and the exact source they determine."""

    payload_sequence: str
    arm_length_bp: int
    independent_domains: tuple[tuple[str, ...], ...]
    source_expression: SequenceExpression
    junction_boundary: int
    terminus_boundary: int
    enzyme_bindings: tuple[FoldbackEnzymeBinding, ...]

    @property
    def cardinality(self) -> int:
        """Count assignments before reaction-stage admission."""
        return prod(len(domain) for domain in self.independent_domains)

    def materialize(self, sequence: str) -> FoldbackSequenceSolution:
        """Recover one exact source and hairpin from independent arm/cap bases."""
        if len(sequence) != len(self.independent_domains):
            raise ValueError("Independent sequence length differs from the foldback domain.")
        if any(
            base not in domain
            for base, domain in zip(sequence, self.independent_domains, strict=True)
        ):
            raise ValueError("Independent sequence lies outside the foldback domain.")
        source = "".join(
            base
            if isinstance(base, str)
            else reverse_complement_iupac(sequence[base.index])
            if base.complemented
            else sequence[base.index]
            for base in self.source_expression
        )
        arm = sequence[: self.arm_length_bp]
        return FoldbackSequenceSolution(
            source_reference_sequence=source,
            retained_sequence=self.payload_sequence
            + sequence
            + reverse_complement_iupac(arm)
            + reverse_complement_iupac(self.payload_sequence),
            loop_sequence=sequence[self.arm_length_bp :],
            foldback_arm_sequence=reverse_complement_iupac(arm),
            junction_boundary=self.junction_boundary,
            terminus_boundary=self.terminus_boundary,
            enzyme_bindings=self.enzyme_bindings,
        )

    def mirrored(self) -> FoldbackSequenceDomain:
        """Mirror the source without changing independent final-product bases."""
        source_nt = len(self.source_expression)
        return replace(
            self,
            source_expression=reverse_complement_expression(self.source_expression),
            junction_boundary=source_nt - self.junction_boundary,
            terminus_boundary=source_nt - self.terminus_boundary,
            enzyme_bindings=tuple(
                mirror_binding(binding, source_nt=source_nt) for binding in self.enzyme_bindings
            ),
        )


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


def solve_foldback_sequence_domain(
    *,
    payload_sequence: str,
    target: FoldbackTarget,
    program: FoldbackProgramCandidate,
) -> FoldbackSequenceDomain | FoldbackPlacementFailure:
    """Solve finite base domains without enumerating concrete sequence members."""
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Foldback sequence discovery requires one exact nick strand.")
    if target.nick_strand is Strand.BOTTOM:
        if program.nick_orientation is not SiteOrientation.REVERSE:
            return FoldbackPlacementFailure(code="foldback-nick-orientation-unavailable")
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
        domain = solve_foldback_sequence_domain(
            payload_sequence=payload_sequence,
            target=mirrored_target,
            program=mirrored_program,
        )
        return domain if isinstance(domain, FoldbackPlacementFailure) else domain.mirrored()
    if program.nick_orientation is not SiteOrientation.FORWARD:
        return FoldbackPlacementFailure(code="foldback-nick-orientation-unavailable")
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
        return FoldbackPlacementFailure(code="foldback-nick-orientation-unavailable")
    bindings = [nick_binding]
    if nick_binding.recognition_span.end.offset > terminus:
        return FoldbackPlacementFailure(
            code=(
                "single-cleavage-site-exceeds-source-terminus"
                if program.kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE
                else "foldback-nick-site-exceeds-terminated-substrate"
            )
        )
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
            return FoldbackPlacementFailure(code="terminus-orientation-unavailable")
        if terminus_binding.reference_cut != Boundary(
            offset=terminus
        ) or terminus_binding.complement_cut != Boundary(offset=terminus):
            return FoldbackPlacementFailure(code="unsupported-staggered-terminus")
        bindings.append(terminus_binding)

    if any(binding.recognition_span.start.offset < payload_nt for binding in bindings):
        return FoldbackPlacementFailure(code="payload-recognition-conflict")
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
        return FoldbackPlacementFailure(code="terminus-cleavage-at-source-end")
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
        return FoldbackPlacementFailure(code="overlapping-sequence-conflict")
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
        return FoldbackPlacementFailure(code="foldback-pairing-conflict")
    canonical_source = tuple(next(base for base in _BASES if base in domain) for domain in domains)
    foldback_expression: SequenceExpression = tuple(
        SequenceVariable(index) for index in range(arm_nt + target.loop_length_nt)
    ) + tuple(SequenceVariable(index, True) for index in reversed(range(arm_nt)))
    expression = (
        canonical_source[:junction]
        + reverse_complement_expression(foldback_expression[target.junction_offset_nt :])
        + canonical_source[terminus:]
    )
    return FoldbackSequenceDomain(
        payload_sequence=payload_sequence,
        arm_length_bp=arm_nt,
        independent_domains=(*arm_domains, *loop_domains),
        source_expression=expression,
        junction_boundary=junction,
        terminus_boundary=terminus,
        enzyme_bindings=tuple(bindings),
    )
