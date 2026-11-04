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

from hop_design.models.construction import (
    BasalTarget,
    ConstructionEndpoint,
    SequenceDomainPartition,
)

from ..sequence_index import candidate_range
from .domains import solve_basal_sequence_domain
from .programs import (
    BasalPlacementFailure,
    BasalProgramCandidate,
    BasalSequenceSolution,
)
from .sequence_index import BasalSequenceIndex


def basal_retained_overhead_nt(
    *,
    target: BasalTarget,
    endpoint: ConstructionEndpoint,
) -> int:
    """Return the non-payload span retained in the local PCR reference state."""
    if endpoint not in {
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        ConstructionEndpoint.ADAPTER_LIGATED_HAIRPIN,
        ConstructionEndpoint.CLONE_READY_DUPLEX,
    }:
        raise ValueError("Basal retained-overhead accounting requires a PCR-bearing endpoint.")
    arm_nt = len(target.pairing_constraints)
    return arm_nt + target.nick_offset_nt


def iter_basal_program_solutions(
    *,
    payload_sequence: str,
    target: BasalTarget,
    endpoint: ConstructionEndpoint,
    program: BasalProgramCandidate,
    sequence_partition: SequenceDomainPartition | None = None,
    start: int = 0,
    stop: int | None = None,
) -> Iterator[BasalSequenceSolution | BasalPlacementFailure]:
    """Solve exact source and adapter sequences from geometry and recognition constraints."""
    domain = solve_basal_sequence_domain(
        payload_sequence=payload_sequence, target=target, endpoint=endpoint, program=program
    )
    if isinstance(domain, BasalPlacementFailure):
        for _ in candidate_range(1, start=start, stop=stop, partition=sequence_partition):
            yield domain
        return
    index = BasalSequenceIndex.create(domain)
    for rank in candidate_range(
        index.cardinality, start=start, stop=stop, partition=sequence_partition
    ):
        yield index.member_at(rank)
