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
from hop_design.models.coordinates import Boundary
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.physical import SiteOrientation, Strand
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

from .orientation import mirror_binding, opposite_orientation, oriented_pattern, place_binding
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
    """Retained arm/cap variables followed by variable bases in the cleaved source tail."""

    payload_sequence: str
    arm_length_bp: int
    retained_length_nt: int
    independent_domains: tuple[tuple[str, ...], ...]
    source_expression: SequenceExpression
    junction_boundary: int
    terminus_boundary: int
    enzyme_bindings: tuple[FoldbackEnzymeBinding, ...]

    @property
    def cardinality(self) -> int:
        """Count retained arm/cap assignments before reaction-stage admission."""
        return prod(len(domain) for domain in self.independent_domains[: self.retained_length_nt])

    @property
    def precursor_cardinality(self) -> int:
        """Count complete source assignments, including the tail removed by cleavage."""
        return prod(len(domain) for domain in self.independent_domains)

    def materialize(self, sequence: str) -> FoldbackSequenceSolution:
        """Recover one exact source from all retained and cleaved-tail variables."""
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
            + sequence[: self.retained_length_nt]
            + reverse_complement_iupac(arm)
            + reverse_complement_iupac(self.payload_sequence),
            loop_sequence=sequence[self.arm_length_bp : self.retained_length_nt],
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

    def assignment_of(self, solution: FoldbackSequenceSolution) -> str:
        """Recover retained and cleaved-tail variables from an exact matching source."""
        if len(solution.source_reference_sequence) != len(self.source_expression):
            raise ValueError("Source length differs from the foldback domain.")
        core = reverse_complement_iupac(solution.foldback_arm_sequence) + solution.loop_sequence
        if len(core) != self.retained_length_nt:
            raise ValueError("Retained word length differs from the foldback domain.")
        bases = list(core) + [""] * (len(self.independent_domains) - len(core))
        for expression, base in zip(
            self.source_expression, solution.source_reference_sequence, strict=True
        ):
            if isinstance(expression, SequenceVariable) and expression.index >= len(core):
                bases[expression.index] = (
                    reverse_complement_iupac(base) if expression.complemented else base
                )
        assignment = "".join(bases)
        if self.materialize(assignment) != solution:
            raise ValueError("Source and molecular bindings differ from the foldback domain.")
        return assignment


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

    nick_binding = place_binding(
        program.nick_enzyme,
        role=EnzymeRole.FOLDBACK_NICK,
        orientation=program.nick_orientation,
        controlled_strand=Strand.TOP,
        controlled_boundary=nick,
    )
    if nick_binding is None:
        return FoldbackPlacementFailure(code="foldback-nick-orientation-unavailable")
    if isinstance(nick_binding, FoldbackPlacementFailure):
        return nick_binding
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
        terminus_binding = place_binding(
            program.terminus_enzyme,
            role=EnzymeRole.TERMINUS_DEFINITION,
            orientation=program.terminus_orientation,
            controlled_strand=Strand.BOTTOM,
            controlled_boundary=terminus,
        )
        if terminus_binding is None:
            return FoldbackPlacementFailure(code="terminus-orientation-unavailable")
        if isinstance(terminus_binding, FoldbackPlacementFailure):
            return terminus_binding
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
        pattern = oriented_pattern(enzyme, binding.orientation)
        for offset, symbol in enumerate(pattern):
            coordinate = binding.recognition_span.start.offset + offset
            domains[coordinate] &= iupac_bases(symbol)
    if any(not domain for domain in domains):
        return FoldbackPlacementFailure(code="overlapping-sequence-conflict")
    arm_domain_sets = [set(_BASES) for _ in range(arm_nt)]
    loop_domain_sets = [set(_BASES) for _ in range(target.loop_length_nt)]
    if target.loop_sequence is not None:
        for allowed, base in zip(loop_domain_sets, target.loop_sequence, strict=True):
            allowed.intersection_update({base})
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
    independent_domains = [*arm_domains, *loop_domains]
    tail_expression: list[str | SequenceVariable] = []
    for allowed in domains[terminus:]:
        choices = tuple(base for base in _BASES if base in allowed)
        if len(choices) == 1:
            tail_expression.append(choices[0])
        else:
            tail_expression.append(SequenceVariable(len(independent_domains)))
            independent_domains.append(choices)
    foldback_expression: SequenceExpression = tuple(
        SequenceVariable(index) for index in range(arm_nt + target.loop_length_nt)
    ) + tuple(SequenceVariable(index, True) for index in reversed(range(arm_nt)))
    expression = (
        tuple(payload_sequence)
        + reverse_complement_expression(foldback_expression[target.junction_offset_nt :])
        + tuple(tail_expression)
    )
    return FoldbackSequenceDomain(
        payload_sequence=payload_sequence,
        arm_length_bp=arm_nt,
        retained_length_nt=arm_nt + target.loop_length_nt,
        independent_domains=tuple(independent_domains),
        source_expression=expression,
        junction_boundary=junction,
        terminus_boundary=terminus,
        enzyme_bindings=tuple(bindings),
    )
