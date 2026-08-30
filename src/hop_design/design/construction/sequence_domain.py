"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/sequence_domain.py

Selects disjoint parts of canonical local sequence-solution enumeration.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from hop_design.models.construction import (
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    SequenceDomainPartition,
)


def partition_sequence_domain[Outcome](
    outcomes: Iterable[Outcome],
    partition: SequenceDomainPartition | None,
) -> Iterator[Outcome]:
    """Yield the declared modulo part of one canonical solution stream."""
    if partition is None:
        yield from outcomes
        return
    for canonical_ordinal, outcome in enumerate(outcomes):
        if canonical_ordinal % partition.part_count == partition.part_index:
            yield outcome


def partition_payload_accounting(
    partition: SequenceDomainPartition | None,
    *,
    total_assignments: int,
) -> PayloadCompatibilityAccounting | None:
    """Return conservative payload accounting for one sequence-domain part."""
    if partition is None:
        return None
    return PayloadCompatibilityAccounting(
        status=PayloadCompatibilityStatus.NOT_COMPUTED,
        total_assignments=total_assignments,
        exhaustive=False,
        warning=("One sequence-domain part does not establish whole-domain payload compatibility."),
    )


__all__ = ["partition_payload_accounting", "partition_sequence_domain"]
