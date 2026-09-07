"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/neighborhood_accounting.py

Builds local-search dispositions and payload-compatibility accounting.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from itertools import product

from hop_design.models.construction import (
    FailureReasonCount,
    LocalNeighborhoodRequest,
    OverheadLevelSummary,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchTerminationReason,
)
from hop_design.models.sequence import iupac_bases

_BASES = ("A", "C", "G", "T")


def payload_assignments(request: LocalNeighborhoodRequest) -> Iterator[str]:
    """Yield canonical exact payload assignments for one local request."""
    domains = tuple(
        tuple(base for base in _BASES if base in iupac_bases(symbol))
        for symbol in request.payload.payload.sequence
    )
    for assignment in product(*domains):
        yield "".join(assignment)


def payload_cardinality(request: LocalNeighborhoodRequest) -> int:
    """Return the exact cardinality of the request payload domain."""
    cardinality = 1
    for symbol in request.payload.payload.sequence:
        cardinality *= len(iupac_bases(symbol))
    return cardinality


def search_disposition(
    *, termination: SearchTerminationReason | None, has_results: bool
) -> SearchDisposition:
    """Describe completion and feasibility without conflating the two."""
    if termination is None:
        return SearchDisposition(
            completion=SearchCompletionStatus.COMPLETE,
            feasibility=(
                SearchFeasibilityStatus.FEASIBLE
                if has_results
                else SearchFeasibilityStatus.INFEASIBLE
            ),
            termination_reason=SearchTerminationReason.EXHAUSTED_DOMAIN,
        )
    if termination is SearchTerminationReason.RESULT_QUOTA:
        return SearchDisposition(
            completion=SearchCompletionStatus.STOPPED_BY_POLICY,
            feasibility=SearchFeasibilityStatus.FEASIBLE,
            termination_reason=termination,
        )
    return SearchDisposition(
        completion=SearchCompletionStatus.TRUNCATED,
        feasibility=(
            SearchFeasibilityStatus.FEASIBLE if has_results else SearchFeasibilityStatus.UNKNOWN
        ),
        termination_reason=termination,
    )


def payload_accounting(
    *,
    request: LocalNeighborhoodRequest,
    has_records: bool,
    compatible_payloads: set[str],
    payload_failures: dict[str, set[str]],
    payload_total: int,
    partition_accounting: PayloadCompatibilityAccounting | None,
    incomplete: bool,
    incomplete_warning: str,
    recognition_failure_code: str,
    recognition_conflict_code: str,
    no_realization_code: str,
) -> PayloadCompatibilityAccounting:
    """Account for payload compatibility across an exhausted or bounded search."""
    if incomplete:
        return PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.NOT_COMPUTED,
            total_assignments=payload_total,
            exhaustive=False,
            warning=incomplete_warning,
        )
    if partition_accounting is not None:
        return partition_accounting
    if has_records:
        excluded = payload_total - len(compatible_payloads)
        conflicts = Counter(
            code
            for payload, codes in payload_failures.items()
            if payload not in compatible_payloads
            for code in codes
        )
        return PayloadCompatibilityAccounting(
            status=PayloadCompatibilityStatus.COMPLETE,
            total_assignments=payload_total,
            compatible_assignments=len(compatible_payloads),
            excluded_assignments=excluded,
            conflict_counts=tuple(
                FailureReasonCount(code=code, count=count)
                for code, count in sorted(conflicts.items())
                if count <= excluded
            ),
            exhaustive=True,
        )
    payload_conflicts = Counter(
        (
            recognition_conflict_code
            if recognition_failure_code in payload_failures[payload]
            else no_realization_code
        )
        for payload in payload_assignments(request)
    )
    return PayloadCompatibilityAccounting(
        status=PayloadCompatibilityStatus.COMPLETE,
        total_assignments=payload_total,
        compatible_assignments=0,
        excluded_assignments=payload_total,
        conflict_counts=tuple(
            FailureReasonCount(code=code, count=count)
            for code, count in sorted(payload_conflicts.items())
        ),
        exhaustive=True,
    )


def reject_partial_payload_routes[Realization](
    *,
    records: tuple[Realization, ...],
    levels: list[OverheadLevelSummary],
    rejected_count: int,
    failures: Counter[str],
) -> tuple[tuple[Realization, ...], list[OverheadLevelSummary], int, Counter[str]]:
    """Move partial-payload realizations into the rejected accounting partition."""
    code = "all-members-compatibility-required"
    failures[code] += len(records)
    updated: list[OverheadLevelSummary] = []
    for level in levels:
        level_failures = Counter({reason.code: reason.count for reason in level.failure_reasons})
        if level.realization_ids:
            level_failures[code] += len(level.realization_ids)
        updated.append(
            OverheadLevelSummary(
                retained_overhead_nt=level.retained_overhead_nt,
                examined=level.examined,
                complete=level.complete,
                candidate_count=level.candidate_count,
                realization_ids=(),
                rejected_count=level.rejected_count + len(level.realization_ids),
                failure_reasons=tuple(
                    FailureReasonCount(code=reason, count=count)
                    for reason, count in sorted(level_failures.items())
                ),
            )
        )
    return (), updated, rejected_count + len(records), failures


__all__ = [
    "payload_accounting",
    "payload_assignments",
    "payload_cardinality",
    "reject_partial_payload_routes",
    "search_disposition",
]
