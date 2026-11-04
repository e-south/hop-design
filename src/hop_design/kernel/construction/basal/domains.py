"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/basal/domains.py

Solves basal source and adapter domains before exact sequence materialization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.construction import BasalPairAllowance, BasalTarget, ConstructionEndpoint
from hop_design.models.construction.enzyme_binding import ConstructionEnzymeBinding
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.junction import Strand
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import normalize_dna_sequence, reverse_complement_iupac

from .pairing import resolve_basal_pairing_state
from .programs import (
    _BASES,
    BasalPlacementFailure,
    BasalProgramCandidate,
    BasalSequenceSolution,
    _adapter_domains,
    _binding,
    _constrain,
    _oriented_cuts,
    _oriented_pattern,
)


@dataclass(frozen=True, slots=True)
class BasalSequenceDomain:
    """Exact placement domains, including source context outside the retained window."""

    target: BasalTarget
    program: BasalProgramCandidate
    payload_sequence: str
    base_domains: tuple[tuple[str, ...], ...]
    source_span: Span
    payload_span: Span
    adapter_span: Span
    source_arm_domains: tuple[tuple[str, ...], ...]
    unresolved_indexes: tuple[int, ...]
    adapter_end_bases: tuple[tuple[int, str], ...]
    enzyme_bindings: tuple[ConstructionEnzymeBinding, ...]
    deferred_end_sequence: bool = False

    @property
    def variable_indexes(self) -> tuple[int, ...]:
        """Return the ordered source arm positions paired with the adapter."""
        return tuple(range(self.source_span.start.offset, self.source_span.end.offset))

    def permits_adapter(self, source_arm: str, adapter: str | None) -> bool:
        """Check exact pairing permissions, future-end bases, and placement masks."""
        arm_nt = len(self.source_arm_domains)
        if self.adapter_span.start == self.adapter_span.end:
            return adapter is None
        if adapter is None or len(adapter) != arm_nt:
            return False
        return all(
            base in _adapter_domains(source_arm[arm_nt - 1 - position], constraint=constraint)
            and base in self.base_domains[self.adapter_span.start.offset + position]
            for position, (base, constraint) in enumerate(
                zip(adapter, self.target.pairing_constraints, strict=True)
            )
        ) and all(
            adapter[position] == base
            for position, base in self.adapter_end_bases
            if position < len(adapter)
        )

    def canonical_source_domains(self) -> tuple[tuple[str, ...], ...]:
        """Resolve source masks when every adapter position requires canonical pairing."""
        if not self.target.pairing_constraints or any(
            constraint.allowed_class is not BasalPairAllowance.MATCH
            for constraint in self.target.pairing_constraints
        ):
            raise ValueError("Compact basal source domains require canonical pairing permissions.")
        if self.adapter_span.start == self.adapter_span.end:
            raise ValueError("Compact basal source domains require an adapter-bearing endpoint.")
        domains: list[tuple[str, ...]] = [
            (bases[0],) for bases in self.base_domains[: self.adapter_span.start.offset]
        ]
        end_bases = dict(self.adapter_end_bases)
        arm_nt = len(self.source_arm_domains)
        for source_position, source_index in enumerate(self.variable_indexes):
            position = arm_nt - 1 - source_position
            constraint = self.target.pairing_constraints[position]
            domains[source_index] = tuple(
                source
                for source in self.source_arm_domains[source_position]
                if any(
                    adapter in self.base_domains[self.adapter_span.start.offset + position]
                    and (position not in end_bases or adapter == end_bases[position])
                    for adapter in _adapter_domains(source, constraint=constraint)
                )
            )
        for index in self.unresolved_indexes:
            if index < len(domains):
                domains[index] = self.base_domains[index]
        return tuple(domains)

    def materialize(
        self, source: str, adapter: str | None
    ) -> BasalSequenceSolution | BasalPlacementFailure:
        """Recover one placement-compatible molecular solution with exact pairing records."""
        if self.deferred_end_sequence:
            raise ValueError("A deferred end domain is not a materializable molecular candidate.")
        if len(source) != self.adapter_span.start.offset or any(
            base not in domain
            for base, domain in zip(
                source, self.base_domains[: self.adapter_span.start.offset], strict=True
            )
        ):
            raise ValueError("Source sequence lies outside the basal placement domain.")
        complete = source + (adapter or "")
        expected_length = (
            len(self.base_domains) if adapter is not None else self.adapter_span.start.offset
        )
        if len(complete) != expected_length or any(
            base not in domain
            for base, domain in zip(complete, self.base_domains[:expected_length], strict=True)
        ):
            raise ValueError("Source and adapter sequences lie outside the basal placement domain.")
        variable = (
            set(self.variable_indexes)
            | set(self.unresolved_indexes)
            | set(range(self.adapter_span.start.offset, self.adapter_span.end.offset))
        )
        if any(
            index not in variable and base != self.base_domains[index][0]
            for index, base in enumerate(complete)
        ):
            raise ValueError("Source sequence changes fixed basal construction context.")
        source_arm = source[self.source_span.start.offset : self.source_span.end.offset]
        if any(
            base not in domain
            for base, domain in zip(source_arm, self.source_arm_domains, strict=True)
        ):
            raise ValueError("Source arm violates a basal base constraint.")
        paired_adapter = adapter[: len(self.source_arm_domains)] if adapter is not None else None
        if not self.permits_adapter(source_arm, paired_adapter):
            raise ValueError("Adapter sequence lies outside the basal pairing domain.")
        pairing_state = None
        if paired_adapter is not None:
            release_action = self.program.future_release_action
            pairing_state = resolve_basal_pairing_state(
                source_sequence_5prime=source_arm,
                adapter_sequence_5prime=paired_adapter,
                source_span=self.source_span,
                adapter_span=Span(
                    start=Boundary(offset=0), end=Boundary(offset=len(paired_adapter))
                ),
                end_projection_positions=(
                    ()
                    if release_action is None
                    else release_action.paired_end_positions(
                        nick_offset_nt=self.target.nick_offset_nt,
                        pairing_length_nt=len(paired_adapter),
                    )
                ),
            )
            if not self.target.permits_pair_classes(
                pair.pair_class for pair in pairing_state.pairs
            ):
                return BasalPlacementFailure("basal-pair-budget-exceeded")
        return BasalSequenceSolution(
            source_precursor_sequence=source,
            adapter_sequence=adapter,
            payload_span=self.payload_span,
            pairing_state=pairing_state,
            enzyme_bindings=self.enzyme_bindings,
        )

    def materialize_canonical_source(self, source: str) -> BasalSequenceSolution:
        """Recover a canonical adapter and its required recognition context from a source."""
        self.canonical_source_domains()
        arm = source[self.source_span.start.offset : self.source_span.end.offset]
        adapter = reverse_complement_iupac(arm) + "".join(
            bases[0] for bases in self.base_domains[self.adapter_span.end.offset :]
        )
        solution = self.materialize(source, adapter)
        if isinstance(solution, BasalPlacementFailure):
            raise ValueError(f"Canonical basal source failed materialization: {solution.code}.")
        return solution


def solve_basal_sequence_domain(
    *,
    payload_sequence: str,
    target: BasalTarget,
    endpoint: ConstructionEndpoint,
    program: BasalProgramCandidate,
    defer_end_sequence: bool = False,
) -> BasalSequenceDomain | BasalPlacementFailure:
    """Place source and adapter constraints without expanding exact sequence choices."""
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Basal sequence realization requires one exact nick strand.")
    payload = normalize_dna_sequence(payload_sequence, allow_degenerate=False)
    arm_nt = (
        len(target.pairing_constraints)
        if target.pairing_constraints
        else max(1, program.nick_enzyme.recognition_length + target.nick_offset_nt)
    )
    source_start = 0
    payload_start = arm_nt + target.nick_offset_nt
    payload_end = payload_start + len(payload)
    adapter_start = payload_end
    adapter_end = adapter_start + (
        arm_nt if endpoint is not ConstructionEndpoint.SSDNA_HAIRPIN else 0
    )

    nick_pattern = _oriented_pattern(program.nick_enzyme, program.nick_orientation)
    nick_cut_offset = (
        program.nick_enzyme.cut_offset_reference_strand
        if program.nick_orientation is SiteOrientation.FORWARD
        else program.nick_enzyme.recognition_length
        - program.nick_enzyme.cut_offset_reference_strand
    )
    nick_boundary = payload_start - target.nick_offset_nt
    nick_site_start = nick_boundary - nick_cut_offset
    reference_cut, complement_cut = _oriented_cuts(
        program.nick_enzyme,
        orientation=program.nick_orientation,
        site_start=nick_site_start,
    )

    placements: list[tuple[int, str]] = [(nick_site_start, nick_pattern), (payload_start, payload)]
    release_action = program.future_release_action
    adapter_end_bases: tuple[tuple[int, str], ...] = ()
    if release_action is not None:
        end_placement = release_action.source_end_placement(
            payload_boundary=payload_start, nick_offset_nt=target.nick_offset_nt
        )
        if end_placement is not None:
            start, word = end_placement
            placements.append((start, "N" * len(word) if defer_end_sequence else word))
        if not defer_end_sequence:
            adapter_end_bases = release_action.adapter_end_bases(
                nick_offset_nt=target.nick_offset_nt
            )
    if (
        release_action is not None
        and release_action.requirement.recognition_material == "source_duplex"
    ):
        placements.append(
            release_action.source_recognition_placement(payload_boundary=payload_start)
        )
    cut_boundaries = tuple(
        boundary for boundary in (reference_cut, complement_cut) if boundary is not None
    )
    minimum = min(0, *(start for start, _pattern in placements), *cut_boundaries)
    maximum = max(
        adapter_end,
        *(start + len(pattern) for start, pattern in placements),
        *cut_boundaries,
    )
    shift = -minimum
    source_start += shift
    nick_boundary += shift
    payload_start += shift
    payload_end += shift
    adapter_start += shift
    adapter_end += shift
    nick_site_start += shift
    placements = [(start + shift, pattern) for start, pattern in placements]
    domains = [set(_BASES) for _ in range(maximum - minimum)]
    recognition_indexes: set[int] = set()
    for start, pattern in placements:
        recognition_indexes.update(range(start, start + len(pattern)))
        if not _constrain(domains, start=start, pattern=pattern):
            return BasalPlacementFailure("recognition-payload-conflict")
    if (
        release_action is not None
        and release_action.requirement.recognition_material == "source_duplex"
    ):
        recognition_indexes.update(range(adapter_start))

    recognition_indexes.update(range(nick_boundary, payload_start))
    variable_indexes = tuple(range(source_start, nick_boundary))
    source_domains = tuple(
        tuple(
            base
            for base in _BASES
            if base in domains[index]
            and base in target.pairing_constraints[arm_nt - 1 - source_index].allowed_source_bases
        )
        for source_index, index in enumerate(variable_indexes)
    )
    if any(not domain for domain in source_domains):
        return BasalPlacementFailure("basal-source-conflict")
    assigned_indexes = {
        *variable_indexes,
        *range(payload_start, payload_end),
        *range(adapter_start, adapter_end),
    }
    unresolved_indexes = tuple(
        index for index in sorted(recognition_indexes - assigned_indexes) if len(domains[index]) > 1
    )
    return BasalSequenceDomain(
        target=target,
        program=program,
        payload_sequence=payload,
        base_domains=tuple(tuple(base for base in _BASES if base in domain) for domain in domains),
        source_span=Span(start=Boundary(offset=source_start), end=Boundary(offset=nick_boundary)),
        payload_span=Span(start=Boundary(offset=payload_start), end=Boundary(offset=payload_end)),
        adapter_span=Span(start=Boundary(offset=adapter_start), end=Boundary(offset=adapter_end)),
        source_arm_domains=source_domains,
        unresolved_indexes=unresolved_indexes,
        adapter_end_bases=adapter_end_bases,
        deferred_end_sequence=defer_end_sequence,
        enzyme_bindings=(
            _binding(
                enzyme=program.nick_enzyme,
                role=EnzymeRole.BASAL_NICK,
                strand=target.nick_strand,
                orientation=program.nick_orientation,
                start=nick_site_start,
            ),
        ),
    )
