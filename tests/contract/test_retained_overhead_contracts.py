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

from hop_design.design.construction.overhead import foldback_overhead_levels
from hop_design.models.construction import (
    FoldbackGeometryDomain,
    FoldbackTarget,
    LocalNeighborhoodRequest,
    NeighborhoodSearchPlan,
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


def test_foldback_geometry_uses_payload_boundary_junction_offset() -> None:
    geometry = FoldbackTarget(
        junction_offset_nt=0,
        loop_length_nt=3,
        annealing_arm_length_bp=3,
    )

    assert geometry.junction_offset_nt == 0
    with pytest.raises(ValidationError):
        FoldbackTarget.model_validate(
            {
                "nick_offset_within_foldback_nt": 0,
                "loop_length_nt": 3,
                "annealing_arm_length_bp": 3,
            }
        )


def test_foldback_search_enumerates_every_geometry_at_each_absolute_overhead() -> None:
    levels = foldback_overhead_levels(
        FoldbackGeometryDomain(),
        NeighborhoodSearchPlan(
            max_retained_overhead_nt=11,
            max_search_nodes=100,
            max_realizations=100,
        ),
    )

    assert tuple(level.retained_overhead_nt for level in levels) == tuple(range(12))
    assert levels[8].geometries == ()
    assert [
        (
            item.junction_offset_nt,
            item.loop_length_nt,
            item.annealing_arm_length_bp,
        )
        for item in levels[9].geometries
    ] == [(0, 3, 3)]
    assert [
        (item.loop_length_nt, item.annealing_arm_length_bp) for item in levels[11].geometries
    ] == [(3, 4), (5, 3)]


def test_foldback_search_respects_exact_advanced_geometry_restrictions() -> None:
    levels = foldback_overhead_levels(
        FoldbackGeometryDomain(
            junction_offsets_nt=(0,),
            loop_lengths_nt=(4,),
            annealing_arm_lengths_bp=(3,),
        ),
        NeighborhoodSearchPlan(
            max_retained_overhead_nt=12,
            max_search_nodes=100,
            max_realizations=100,
        ),
    )

    assert [
        (level.retained_overhead_nt, len(level.geometries)) for level in levels if level.geometries
    ] == [(10, 1)]


def test_result_quota_is_explicit_and_not_an_exhaustive_search_default() -> None:
    assert (
        NeighborhoodSearchPlan(
            max_retained_overhead_nt=20,
            max_search_nodes=100,
            max_realizations=100,
        ).result_quota
        is None
    )

    with pytest.raises(ValidationError, match="result_quota"):
        NeighborhoodSearchPlan(
            max_retained_overhead_nt=20,
            max_search_nodes=100,
            max_realizations=100,
            stop="result_quota",
        )


def test_local_request_exposes_one_geometry_domain_and_retained_overhead_plan() -> None:
    assert "geometry_domain" in LocalNeighborhoodRequest.model_fields
    assert "search" in LocalNeighborhoodRequest.model_fields
    assert "target" not in LocalNeighborhoodRequest.model_fields
    assert "relaxation" not in LocalNeighborhoodRequest.model_fields
    assert "enumeration" not in LocalNeighborhoodRequest.model_fields


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
