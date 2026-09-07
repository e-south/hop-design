"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_retained_overhead_contracts.py

Tests retained-overhead accounting and bounded-search disposition contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.models.construction import (
    OverheadPosition,
    RetainedOverheadLedger,
    SearchCompletionStatus,
    SearchDisposition,
    SearchFeasibilityStatus,
    SearchTerminationReason,
)


def _position(*, coordinate: int, base: str = "A") -> OverheadPosition:
    return OverheadPosition(
        coordinate_space="foldback-path",
        position=coordinate,
        base=base,
        material_role="source",
    )


def test_retained_overhead_ledger_counts_explicit_non_payload_positions() -> None:
    ledger = RetainedOverheadLedger(
        neighborhood="foldback",
        reference_state_id="foldback-product",
        positions=tuple(_position(coordinate=index) for index in range(9)),
        retained_overhead_nt=9,
    )

    assert ledger.retained_overhead_nt == 9
    assert ledger.positions[0].base == "A"


def test_retained_overhead_ledger_rejects_duplicate_positions_or_count_drift() -> None:
    position = _position(coordinate=0)

    with pytest.raises(ValidationError, match="unique"):
        RetainedOverheadLedger(
            neighborhood="foldback",
            reference_state_id="foldback-product",
            positions=(position, position),
            retained_overhead_nt=2,
        )

    with pytest.raises(ValidationError, match="equal"):
        RetainedOverheadLedger(
            neighborhood="foldback",
            reference_state_id="foldback-product",
            positions=(position,),
            retained_overhead_nt=2,
        )


@pytest.mark.parametrize(
    ("completion", "feasibility", "reason"),
    (
        ("complete", "feasible", "exhausted_domain"),
        ("complete", "infeasible", "exhausted_domain"),
        ("stopped_by_policy", "feasible", "result_quota"),
        ("stopped_by_policy", "unknown", "requested_quota"),
        ("truncated", "feasible", "evaluation_cap"),
        ("truncated", "unknown", "interruption"),
    ),
)
def test_search_disposition_accepts_truthful_completion_and_feasibility_pairs(
    completion: str,
    feasibility: str,
    reason: str,
) -> None:
    result = SearchDisposition(
        completion=SearchCompletionStatus(completion),
        feasibility=SearchFeasibilityStatus(feasibility),
        termination_reason=SearchTerminationReason(reason),
    )

    assert result.completion is SearchCompletionStatus(completion)
    assert result.feasibility is SearchFeasibilityStatus(feasibility)
    assert result.termination_reason is SearchTerminationReason(reason)


@pytest.mark.parametrize(
    ("completion", "feasibility", "reason"),
    (
        ("complete", "unknown", "exhausted_domain"),
        ("complete", "feasible", "evaluation_cap"),
        ("stopped_by_policy", "infeasible", "result_quota"),
        ("truncated", "infeasible", "interruption"),
    ),
)
def test_search_disposition_rejects_claims_stronger_than_coverage(
    completion: str,
    feasibility: str,
    reason: str,
) -> None:
    with pytest.raises(ValidationError):
        SearchDisposition(
            completion=SearchCompletionStatus(completion),
            feasibility=SearchFeasibilityStatus(feasibility),
            termination_reason=SearchTerminationReason(reason),
        )
