from __future__ import annotations

import json
from pathlib import Path

import pytest

from hop_design.design.foldback import evaluate_foldback, search_foldback_arms
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.foldback import (
    FoldbackConstraints,
    FoldbackEvaluationRequest,
    FoldbackSearchLimits,
    FoldbackSearchRequest,
    FoldbackSearchResult,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "foldback" / "parity-v1.json"


def _span(bounds: list[int]) -> Span:
    return Span(start=Boundary(offset=bounds[0]), end=Boundary(offset=bounds[1]))


def _constraints(*, max_mismatches: int) -> FoldbackConstraints:
    return FoldbackConstraints(
        max_mismatches=max_mismatches,
        terminal_paired_bp_min=0,
        terminal_paired_bp_max=4,
        max_uninterrupted_paired_bp=4,
        max_added_nt=5,
        required_turn_nt=3,
        allow_protected_region_mismatches=False,
    )


def _request(case: dict[str, object], *, max_mismatches: int) -> FoldbackEvaluationRequest:
    return FoldbackEvaluationRequest(
        precursor_sequence=case["precursor_sequence"],
        nick_boundary=Boundary(offset=case["nick_boundary"]),
        retained_tract_span=_span(case["retained_tract"]),
        protected_region=_span(case["protected_region"]),
        turn_extension=case["turn_extension"],
        foldback_arm=case["foldback_arm"],
        constraints=_constraints(max_mismatches=max_mismatches),
    )


def test_foldback_evaluation_matches_sanitized_exact_fixture() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]

    evaluation = evaluate_foldback(_request(case, max_mismatches=0))

    assert evaluation.report.status == "valid"
    assert evaluation.designed_sequence == case["expected_designed_sequence"]
    assert evaluation.source_turn_sequence == case["expected_source_turn"]
    assert evaluation.effective_turn_sequence == case["expected_effective_turn"]
    assert evaluation.mismatch_positions == ()
    assert evaluation.terminal_paired_bp == 4
    assert evaluation.max_uninterrupted_paired_bp == 4
    assert [(pair.left_index, pair.right_index) for pair in evaluation.junction.pairs] == [
        (0, 10),
        (1, 9),
        (2, 8),
        (3, 7),
    ]


def test_foldback_evaluation_preserves_near_match_measurements() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_near_match"]

    evaluation = evaluate_foldback(_request(case, max_mismatches=1))

    assert evaluation.report.status == "valid"
    assert list(evaluation.mismatch_positions) == case["expected_mismatch_positions"]
    assert evaluation.terminal_paired_bp == case["expected_terminal_paired_bp"]
    assert evaluation.max_uninterrupted_paired_bp == case["expected_max_uninterrupted_paired_bp"]
    assert len(evaluation.junction.pairs) == evaluation.retained_tract_span.length.value
    assert sum(pair.is_match for pair in evaluation.junction.pairs) == 3


def test_foldback_reports_independent_constraint_failures_with_stable_codes() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = dict(fixture["accepted_near_match"])
    case["protected_region"] = [3, 5]

    evaluation = evaluate_foldback(_request(case, max_mismatches=0))

    assert evaluation.report.status == "infeasible"
    assert [item.code for item in evaluation.report.diagnostics] == [
        "HOP-FOLD-002",
        "HOP-FOLD-003",
    ]


def test_foldback_requires_retained_tract_to_begin_at_nick_boundary() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = dict(fixture["accepted_exact"])
    case["retained_tract"] = [1, 5]

    evaluation = evaluate_foldback(_request(case, max_mismatches=0))

    assert evaluation.report.status == "infeasible"
    assert evaluation.report.diagnostics[0].code == "HOP-FOLD-001"


def test_foldback_evaluation_rejects_nick_geometry_report_drift() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    evaluation = evaluate_foldback(_request(case, max_mismatches=0))
    serialized = evaluation.model_dump(mode="json")
    serialized["nick_boundary"] = {"offset": evaluation.nick_boundary.offset - 1}

    with pytest.raises(ValueError, match="HOP-FOLD-001"):
        type(evaluation).model_validate_json(json.dumps(serialized))


def test_foldback_search_is_exact_first_bounded_and_never_silently_truncated() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    request = FoldbackSearchRequest(
        precursor_sequence=case["precursor_sequence"],
        nick_boundary=Boundary(offset=case["nick_boundary"]),
        retained_tract_span=_span(case["retained_tract"]),
        protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
        turn_extension=case["turn_extension"],
        constraints=_constraints(max_mismatches=1),
    )

    result = search_foldback_arms(
        request,
        limits=FoldbackSearchLimits(max_search_nodes=20, max_hits=2),
    )

    assert result.status == "truncated"
    assert result.truncated_by == "max_hits"
    assert result.candidate_space_size == 13
    assert result.search_nodes_examined == 2
    assert result.hits[0].foldback_arm == "CTGA"
    assert result.hits[0].mismatch_positions == ()
    assert result.hits[1].foldback_arm == "ATGA"
    assert result.hits[1].mismatch_positions == (3,)


def test_foldback_search_reports_node_budget_truncation() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    request = FoldbackSearchRequest(
        precursor_sequence=case["precursor_sequence"],
        nick_boundary=Boundary(offset=case["nick_boundary"]),
        retained_tract_span=_span(case["retained_tract"]),
        protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
        turn_extension=case["turn_extension"],
        constraints=_constraints(max_mismatches=1),
    )

    result = search_foldback_arms(
        request,
        limits=FoldbackSearchLimits(max_search_nodes=2, max_hits=20),
    )

    assert result.status == "truncated"
    assert result.truncated_by == "max_search_nodes"
    assert result.search_nodes_examined == 2


def test_foldback_reports_run_length_addition_and_turn_failures_together() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    request = _request(case, max_mismatches=0)
    constrained = request.model_copy(
        update={
            "constraints": FoldbackConstraints(
                max_mismatches=0,
                terminal_paired_bp_min=5,
                terminal_paired_bp_max=5,
                max_uninterrupted_paired_bp=3,
                max_added_nt=4,
                required_turn_nt=2,
                allow_protected_region_mismatches=False,
            )
        }
    )

    evaluation = evaluate_foldback(constrained)

    assert [item.code for item in evaluation.report.diagnostics] == [
        "HOP-FOLD-004",
        "HOP-FOLD-005",
        "HOP-FOLD-006",
        "HOP-FOLD-007",
    ]


def test_foldback_search_distinguishes_complete_from_infeasible() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    base_request = FoldbackSearchRequest(
        precursor_sequence=case["precursor_sequence"],
        nick_boundary=Boundary(offset=case["nick_boundary"]),
        retained_tract_span=_span(case["retained_tract"]),
        protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
        turn_extension=case["turn_extension"],
        constraints=_constraints(max_mismatches=0),
    )

    complete = search_foldback_arms(
        base_request,
        limits=FoldbackSearchLimits(max_search_nodes=1, max_hits=1),
    )
    infeasible = search_foldback_arms(
        base_request.model_copy(
            update={
                "constraints": base_request.constraints.model_copy(update={"required_turn_nt": 99})
            }
        ),
        limits=FoldbackSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert complete.status == "complete"
    assert complete.truncated_by is None
    assert infeasible.status == "infeasible"
    assert infeasible.hits == ()


def test_foldback_search_result_rejects_untruthful_terminal_states() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    hit = evaluate_foldback(_request(case, max_mismatches=0))

    for status, hits, examined in (
        ("complete", (), 0),
        ("infeasible", (hit,), 1),
        ("complete", (hit,), 0),
        ("infeasible", (), 0),
    ):
        try:
            FoldbackSearchResult(
                status=status,
                hits=hits,
                candidate_space_size=1,
                search_nodes_examined=examined,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected inconsistent {status!r} search result to fail.")

    for truncated_by, hits in (("max_hits", ()), ("max_search_nodes", ())):
        try:
            FoldbackSearchResult(
                status="truncated",
                hits=hits,
                candidate_space_size=1,
                search_nodes_examined=1,
                truncated_by=truncated_by,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Expected an untruthful truncated result to fail.")
