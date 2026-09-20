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
    SequenceDomainPartition,
)

from .domains import solve_basal_sequence_domain
from .programs import (
    BasalPlacementFailure,
    BasalProgramCandidate,
    BasalSequenceSolution,
    _adapter_domains,
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
    _ = program
    arm_nt = len(target.pairing_constraints)
    return arm_nt + target.nick_offset_nt


def iter_basal_program_solutions(
    *,
    payload_sequence: str,
    target: BasalTarget,
    endpoint: ConstructionEndpoint,
    program: BasalProgramCandidate,
    sequence_partition: SequenceDomainPartition | None = None,
) -> Iterator[BasalSequenceSolution | BasalPlacementFailure]:
    """Solve exact source and adapter sequences from geometry and recognition constraints."""
    domain = solve_basal_sequence_domain(
        payload_sequence=payload_sequence, target=target, endpoint=endpoint, program=program
    )
    if isinstance(domain, BasalPlacementFailure):
        if sequence_partition is None or sequence_partition.part_index == 0:
            yield domain
        return
    arm_nt = len(domain.source_arm_domains)
    canonical_ordinal = 0
    unresolved_domains = tuple(domain.base_domains[index] for index in domain.unresolved_indexes)
    for source_assignment in product(*domain.source_arm_domains):
        source_arm = "".join(source_assignment)
        if endpoint is ConstructionEndpoint.SSDNA_HAIRPIN:
            adapter_assignments: Iterator[tuple[str, ...]] = iter(((),))
        else:
            per_position = tuple(
                _adapter_domains(source_arm[arm_nt - 1 - position], constraint=constraint)
                for position, constraint in enumerate(target.pairing_constraints)
            )
            if any(not allowed for allowed in per_position):
                continue
            adapter_assignments = product(*per_position)
        for adapter_assignment in adapter_assignments:
            adapter = "".join(adapter_assignment) if adapter_assignment else None
            if not domain.permits_adapter(source_arm, adapter):
                continue
            for unresolved_assignment in product(*unresolved_domains):
                ordinal = canonical_ordinal
                canonical_ordinal += 1
                if (
                    sequence_partition is not None
                    and ordinal % sequence_partition.part_count != sequence_partition.part_index
                ):
                    continue
                bases = [bases[0] for bases in domain.base_domains]
                for index, base in zip(domain.variable_indexes, source_assignment, strict=True):
                    bases[index] = base
                if adapter is not None:
                    for index, base in enumerate(adapter, start=domain.adapter_span.start.offset):
                        bases[index] = base
                for index, base in zip(
                    domain.unresolved_indexes, unresolved_assignment, strict=True
                ):
                    bases[index] = base
                complete = "".join(bases)
                yield domain.materialize(
                    complete[: domain.adapter_span.start.offset],
                    complete[domain.adapter_span.start.offset :] if adapter is not None else None,
                )
