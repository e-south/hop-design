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
    BasalTarget,
    ConstructionEndpoint,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.enzymes import (
    EnzymeRole,
)
from hop_design.models.junction import Strand
from hop_design.models.physical import SiteOrientation
from hop_design.models.sequence import normalize_dna_sequence

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


def iter_basal_program_solutions(
    *,
    payload_sequence: str,
    target: BasalTarget,
    endpoint: ConstructionEndpoint,
    program: BasalProgramCandidate,
) -> Iterator[BasalSequenceSolution | BasalPlacementFailure]:
    """Solve exact source and adapter sequences from geometry and recognition constraints."""
    from .pairing import resolve_basal_pairing_profile

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
    left_site_start: int | None = None
    right_site_start: int | None = None
    if endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
        if (
            target.end_generation is None
            or program.end_enzyme is None
            or program.left_end_orientation is None
            or program.right_end_orientation is None
        ):
            yield BasalPlacementFailure("end-generation-unavailable")
            return
        left_offsets = tuple(
            value
            for value in _oriented_cuts(
                program.end_enzyme, orientation=program.left_end_orientation, site_start=0
            )
            if value is not None
        )
        right_offsets = tuple(
            value
            for value in _oriented_cuts(
                program.end_enzyme, orientation=program.right_end_orientation, site_start=0
            )
            if value is not None
        )
        offset = target.end_generation.type_iis_cut_offset_nt
        left_site_start = source_start - offset - min(left_offsets)
        right_site_start = adapter_end + offset - max(right_offsets)
        placements.extend(
            (
                (
                    left_site_start,
                    _oriented_pattern(program.end_enzyme, program.left_end_orientation),
                ),
                (
                    right_site_start,
                    _oriented_pattern(program.end_enzyme, program.right_end_orientation),
                ),
            )
        )

    minimum = min(0, *(start for start, _pattern in placements))
    maximum = max(adapter_end, *(start + len(pattern) for start, pattern in placements))
    shift = -minimum
    source_start += shift
    payload_start += shift
    payload_end += shift
    adapter_start += shift
    adapter_end += shift
    nick_site_start += shift
    if left_site_start is not None:
        left_site_start += shift
    if right_site_start is not None:
        right_site_start += shift
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
        tuple(base for base in _BASES if base in domains[index]) for index in variable_indexes
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
                _adapter_domains(source_arm[arm_nt - 1 - position], constraint.allowed_class)
                for position, constraint in enumerate(target.pairing_constraints)
            )
            if any(not allowed for allowed in per_position):
                continue
            adapter_assignments = product(*per_position)
        for adapter_assignment in adapter_assignments:
            adapter = "".join(adapter_assignment) if adapter_assignment else None
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
                if (
                    program.end_enzyme is not None
                    and left_site_start is not None
                    and right_site_start is not None
                ):
                    if (
                        program.left_end_orientation is None
                        or program.right_end_orientation is None
                    ):
                        raise RuntimeError("End-generation orientations were lost after placement.")
                    bindings.extend(
                        (
                            _binding(
                                enzyme=program.end_enzyme,
                                role=EnzymeRole.END_GENERATION,
                                strand=None,
                                orientation=program.left_end_orientation,
                                start=left_site_start,
                            ),
                            _binding(
                                enzyme=program.end_enzyme,
                                role=EnzymeRole.END_GENERATION,
                                strand=None,
                                orientation=program.right_end_orientation,
                                start=right_site_start,
                            ),
                        )
                    )
                profile = None
                if adapter is not None:
                    profile = resolve_basal_pairing_profile(
                        source_sequence_5prime=source_arm,
                        adapter_sequence_5prime=adapter,
                        source_span=Span(
                            start=Boundary(offset=source_start),
                            end=Boundary(offset=payload_start),
                        ),
                        adapter_span=Span(start=Boundary(offset=0), end=Boundary(offset=arm_nt)),
                    )
                yield BasalSequenceSolution(
                    source_precursor_sequence=source_precursor,
                    adapter_sequence=adapter_sequence,
                    payload_span=Span(
                        start=Boundary(offset=payload_start), end=Boundary(offset=payload_end)
                    ),
                    pairing_profile=profile,
                    enzyme_bindings=tuple(bindings),
                )
