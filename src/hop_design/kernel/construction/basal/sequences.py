"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/basal/sequences.py

Enumerates exact basal construction programs and sequence solutions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import product

from hop_design.models.construction import (
    BasalFutureReleaseAction,
    BasalTarget,
    ConstructionEndpoint,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    EnzymeRole,
)
from hop_design.models.junction import Strand
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import normalize_dna_sequence, reverse_complement_iupac

from .programs import (
    _BASES,
    BasalPlacementFailure,
    BasalProgramCandidate,
    BasalSequenceSolution,
    _adapter_domains,
    _binding,
    _constrain,
    _oriented_pattern,
)


def basal_retained_overhead_nt(
    *,
    target: BasalTarget,
    endpoint: ConstructionEndpoint,
    program: BasalProgramCandidate,
) -> int:
    """Return the non-payload span retained in the local PCR reference state."""
    if endpoint not in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }:
        raise ValueError("Basal retained-overhead accounting requires a PCR-bearing endpoint.")
    arm_nt = len(target.pairing_constraints)
    nick_cut_offset = (
        program.nick_enzyme.cut_offset_reference_strand
        if program.nick_orientation is SiteOrientation.FORWARD
        else program.nick_enzyme.recognition_length
        - program.nick_enzyme.cut_offset_reference_strand
    )
    nick_boundary = arm_nt - target.nick_offset_nt
    nick_site_start = nick_boundary - nick_cut_offset
    recognition_prefix_nt = max(0, -nick_site_start)
    return recognition_prefix_nt + 2 * arm_nt


def iter_basal_program_solutions(
    *,
    payload_sequence: str,
    target: BasalTarget,
    endpoint: ConstructionEndpoint,
    program: BasalProgramCandidate,
) -> Iterator[BasalSequenceSolution | BasalPlacementFailure]:
    """Solve exact source and adapter sequences from geometry and recognition constraints."""
    from .pairing import resolve_basal_pairing_state

    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Basal sequence realization requires one exact nick strand.")
    payload = normalize_dna_sequence(payload_sequence, allow_degenerate=False)
    arm_nt = (
        len(target.pairing_constraints)
        if target.pairing_constraints
        else max(1, program.nick_enzyme.recognition_length + target.nick_offset_nt)
    )
    source_start = 0
    payload_start = arm_nt
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

    placements: list[tuple[int, str]] = [(nick_site_start, nick_pattern), (payload_start, payload)]
    minimum = min(0, *(start for start, _pattern in placements))
    maximum = max(adapter_end, *(start + len(pattern) for start, pattern in placements))
    shift = -minimum
    source_start += shift
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
            yield BasalPlacementFailure("recognition-payload-conflict")
            return

    variable_indexes = tuple(range(source_start, payload_start))
    source_domains = tuple(
        tuple(
            base
            for base in _BASES
            if base in domains[index]
            and base
            in target.pairing_constraints[arm_nt - 1 - source_index].allowed_source_bases
        )
        for source_index, index in enumerate(variable_indexes)
    )
    if any(not domain for domain in source_domains):
        yield BasalPlacementFailure("basal-source-conflict")
        return
    for source_assignment in product(*source_domains):
        source_arm = "".join(source_assignment)
        if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            adapter_assignments: Iterator[tuple[str, ...]] = iter(((),))
        else:
            per_position = tuple(
                _adapter_domains(
                    source_arm[arm_nt - 1 - position],
                    constraint=constraint,
                )
                for position, constraint in enumerate(target.pairing_constraints)
            )
            if any(not allowed for allowed in per_position):
                continue
            adapter_assignments = product(*per_position)
        for adapter_assignment in adapter_assignments:
            adapter = "".join(adapter_assignment) if adapter_assignment else None
            release_sequence = _future_top_overhang_sequence(program.future_release_action)
            if release_sequence is not None and (
                adapter is None
                or len(release_sequence) > len(adapter)
                or adapter[: len(release_sequence)] != release_sequence
            ):
                continue
            if adapter is not None and any(
                base not in domains[index]
                for index, base in enumerate(adapter, start=adapter_start)
            ):
                continue
            assigned_indexes = {
                *variable_indexes,
                *range(payload_start, payload_end),
                *(range(adapter_start, adapter_end) if adapter is not None else ()),
            }
            unresolved_indexes = tuple(
                index
                for index in sorted(recognition_indexes - assigned_indexes)
                if len(domains[index]) > 1
            )
            unresolved_domains = tuple(
                tuple(base for base in _BASES if base in domains[index])
                for index in unresolved_indexes
            )
            for unresolved_assignment in product(*unresolved_domains):
                bases = [next(base for base in _BASES if base in domain) for domain in domains]
                for index, base in zip(variable_indexes, source_assignment, strict=True):
                    bases[index] = base
                for index, base in enumerate(payload, start=payload_start):
                    bases[index] = base
                if adapter is not None:
                    for index, base in enumerate(adapter, start=adapter_start):
                        bases[index] = base
                for index, base in zip(
                    unresolved_indexes,
                    unresolved_assignment,
                    strict=True,
                ):
                    bases[index] = base
                complete = "".join(bases)
                source_precursor = complete[:adapter_start]
                adapter_sequence = complete[adapter_start:] if adapter is not None else None
                bindings = [
                    _binding(
                        enzyme=program.nick_enzyme,
                        role=EnzymeRole.BASAL_NICK,
                        strand=target.nick_strand,
                        orientation=program.nick_orientation,
                        start=nick_site_start,
                    )
                ]
                pairing_state = None
                if adapter is not None:
                    pairing_state = resolve_basal_pairing_state(
                        source_sequence_5prime=source_arm,
                        adapter_sequence_5prime=adapter,
                        source_span=Span(
                            start=Boundary(offset=source_start),
                            end=Boundary(offset=payload_start),
                        ),
                        adapter_span=Span(start=Boundary(offset=0), end=Boundary(offset=arm_nt)),
                        end_projection_positions=tuple(range(len(release_sequence or ""))),
                    )
                yield BasalSequenceSolution(
                    source_precursor_sequence=source_precursor,
                    adapter_sequence=adapter_sequence,
                    payload_span=Span(
                        start=Boundary(offset=payload_start), end=Boundary(offset=payload_end)
                    ),
                    pairing_state=pairing_state,
                    enzyme_bindings=tuple(bindings),
                )


def _future_top_overhang_sequence(action: BasalFutureReleaseAction | None) -> str | None:
    """Return the future top-strand bases constrained by one cohesive-end requirement."""
    if action is None:
        return None
    requirement = action.requirement
    reference_before_complement = (
        action.reference_cut_from_release_boundary < action.complement_cut_from_release_boundary
    )
    reverse = (reference_before_complement and requirement.product_end == "right") or (
        not reference_before_complement and requirement.product_end == "left"
    )
    return (
        reverse_complement_iupac(requirement.cohesive_end_sequence)
        if reverse
        else requirement.cohesive_end_sequence
    )
