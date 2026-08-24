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


def _constraints(*, max_non_watson_crick_pairs: int) -> FoldbackConstraints:
    return FoldbackConstraints(
        max_non_watson_crick_pairs=max_non_watson_crick_pairs,
        terminal_watson_crick_bp_min=0,
        terminal_watson_crick_bp_max=4,
        max_uninterrupted_watson_crick_bp=4,
        max_added_nt=5,
        required_turn_nt=3,
        allow_protected_region_non_watson_crick_pairs=False,
    )


def _request(
    case: dict[str, object], *, max_non_watson_crick_pairs: int
) -> FoldbackEvaluationRequest:
    retained = _span(case["retained_tract"])
    return FoldbackEvaluationRequest(
        precursor_sequence=case["precursor_sequence"],
        retained_tract_span=retained,
        source_turn_span=Span(
            start=retained.end,
            end=Boundary(offset=len(case["precursor_sequence"])),
        ),
        protected_region=_span(case["protected_region"]),
        turn_extension=case["turn_extension"],
        foldback_arm=case["foldback_arm"],
        constraints=_constraints(max_non_watson_crick_pairs=max_non_watson_crick_pairs),
    )


def test_foldback_evaluation_matches_sanitized_exact_fixture() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]

    evaluation = evaluate_foldback(_request(case, max_non_watson_crick_pairs=0))

    assert evaluation.report.status == "valid"
    assert evaluation.designed_sequence == case["expected_designed_sequence"]
    assert evaluation.source_turn_sequence == case["expected_source_turn"]
    assert evaluation.effective_turn_sequence == case["expected_effective_turn"]
    assert evaluation.non_watson_crick_positions == ()
    assert evaluation.terminal_watson_crick_bp == 4
    assert evaluation.max_uninterrupted_watson_crick_bp == 4
    assert [(pair.left_index, pair.right_index) for pair in evaluation.junction.pairs] == [
        (0, 10),
        (1, 9),
        (2, 8),
        (3, 7),
    ]


def test_foldback_evaluation_preserves_near_match_measurements() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_near_match"]

    evaluation = evaluate_foldback(_request(case, max_non_watson_crick_pairs=1))

    assert evaluation.report.status == "valid"
    assert (
        list(evaluation.non_watson_crick_positions) == case["expected_non_watson_crick_positions"]
    )
    assert evaluation.terminal_watson_crick_bp == case["expected_terminal_watson_crick_bp"]
    assert (
        evaluation.max_uninterrupted_watson_crick_bp
        == case["expected_max_uninterrupted_watson_crick_bp"]
    )
    assert len(evaluation.junction.pairs) == evaluation.retained_tract_span.length.value
    assert sum(pair.is_match for pair in evaluation.junction.pairs) == 3


def test_foldback_pair_kind_is_a_physical_observation() -> None:
    evaluation = evaluate_foldback(
        FoldbackEvaluationRequest(
            precursor_sequence="GAA",
            retained_tract_span=_span([0, 1]),
            source_turn_span=_span([1, 3]),
            protected_region=_span([0, 0]),
            turn_extension="",
            foldback_arm="T",
            constraints=FoldbackConstraints(
                max_non_watson_crick_pairs=1,
                terminal_watson_crick_bp_min=0,
                terminal_watson_crick_bp_max=1,
                max_uninterrupted_watson_crick_bp=1,
                max_added_nt=1,
                required_turn_nt=2,
                allow_protected_region_non_watson_crick_pairs=True,
            ),
        )
    )

    assert evaluation.junction.pairs[0].kind == "gt_wobble"


def test_foldback_request_requires_an_explicit_source_turn_span() -> None:
    request = FoldbackEvaluationRequest(
        precursor_sequence="GAA",
        retained_tract_span=_span([0, 1]),
        source_turn_span=_span([1, 3]),
        protected_region=_span([0, 0]),
        turn_extension="",
        foldback_arm="C",
        constraints=FoldbackConstraints(
            max_non_watson_crick_pairs=0,
            terminal_watson_crick_bp_min=1,
            terminal_watson_crick_bp_max=1,
            max_uninterrupted_watson_crick_bp=1,
            max_added_nt=1,
            required_turn_nt=2,
            allow_protected_region_non_watson_crick_pairs=False,
        ),
    )

    assert evaluate_foldback(request).source_turn_sequence == "AA"

    invalid = request.model_dump(mode="python")
    invalid["source_turn_span"] = _span([1, 2])
    with pytest.raises(ValueError, match="source_turn_span must end at the precursor boundary"):
        FoldbackEvaluationRequest.model_validate(invalid)

    retired = request.model_dump(mode="python")
    retired["nick_boundary"] = {"offset": 0}
    with pytest.raises(ValueError, match="Extra inputs"):
        FoldbackEvaluationRequest.model_validate(retired)


def test_foldback_evaluation_represents_a_cap_only_junction_without_invented_pairs() -> None:
    request = FoldbackEvaluationRequest(
        precursor_sequence="TTAA",
        retained_tract_span=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=0),
        ),
        source_turn_span=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=4),
        ),
        protected_region=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=0),
        ),
        turn_extension="",
        foldback_arm="",
        constraints=FoldbackConstraints(
            max_non_watson_crick_pairs=0,
            terminal_watson_crick_bp_min=0,
            terminal_watson_crick_bp_max=0,
            max_uninterrupted_watson_crick_bp=0,
            max_added_nt=0,
            required_turn_nt=4,
            allow_protected_region_non_watson_crick_pairs=False,
        ),
    )

    evaluation = evaluate_foldback(request)

    assert evaluation.report.status == "valid"
    assert evaluation.junction.sequence == "TTAA"
    assert evaluation.junction.retained_tract_span == _span([0, 0])
    assert evaluation.junction.turn_span == _span([0, 4])
    assert evaluation.junction.foldback_arm_span == _span([4, 4])
    assert evaluation.junction.pairs == ()
    assert evaluation.terminal_watson_crick_bp == 0
    assert evaluation.max_uninterrupted_watson_crick_bp == 0


def test_foldback_reports_independent_constraint_failures_with_stable_codes() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = dict(fixture["accepted_near_match"])
    case["protected_region"] = [3, 5]

    evaluation = evaluate_foldback(_request(case, max_non_watson_crick_pairs=0))

    assert evaluation.report.status == "infeasible"
    assert [item.code for item in evaluation.report.diagnostics] == [
        "HOP-FOLD-001",
        "HOP-FOLD-002",
    ]


def test_foldback_search_is_exact_first_bounded_and_never_silently_truncated() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    request = FoldbackSearchRequest(
        precursor_sequence=case["precursor_sequence"],
        retained_tract_span=_span(case["retained_tract"]),
        source_turn_span=Span(
            start=Boundary(offset=case["retained_tract"][1]),
            end=Boundary(offset=len(case["precursor_sequence"])),
        ),
        protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
        turn_extension=case["turn_extension"],
        constraints=_constraints(max_non_watson_crick_pairs=1),
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
    assert result.hits[0].non_watson_crick_positions == ()
    assert result.hits[1].foldback_arm == "ATGA"
    assert result.hits[1].non_watson_crick_positions == (3,)


def test_foldback_search_reports_node_budget_truncation() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    request = FoldbackSearchRequest(
        precursor_sequence=case["precursor_sequence"],
        retained_tract_span=_span(case["retained_tract"]),
        source_turn_span=Span(
            start=Boundary(offset=case["retained_tract"][1]),
            end=Boundary(offset=len(case["precursor_sequence"])),
        ),
        protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
        turn_extension=case["turn_extension"],
        constraints=_constraints(max_non_watson_crick_pairs=1),
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
    request = _request(case, max_non_watson_crick_pairs=0)
    constrained = request.model_copy(
        update={
            "constraints": FoldbackConstraints(
                max_non_watson_crick_pairs=0,
                terminal_watson_crick_bp_min=5,
                terminal_watson_crick_bp_max=5,
                max_uninterrupted_watson_crick_bp=3,
                max_added_nt=4,
                required_turn_nt=2,
                allow_protected_region_non_watson_crick_pairs=False,
            )
        }
    )

    evaluation = evaluate_foldback(constrained)

    assert [item.code for item in evaluation.report.diagnostics] == [
        "HOP-FOLD-003",
        "HOP-FOLD-004",
        "HOP-FOLD-005",
        "HOP-FOLD-006",
    ]


def test_foldback_search_distinguishes_complete_from_infeasible() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = fixture["accepted_exact"]
    base_request = FoldbackSearchRequest(
        precursor_sequence=case["precursor_sequence"],
        retained_tract_span=_span(case["retained_tract"]),
        source_turn_span=Span(
            start=Boundary(offset=case["retained_tract"][1]),
            end=Boundary(offset=len(case["precursor_sequence"])),
        ),
        protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
        turn_extension=case["turn_extension"],
        constraints=_constraints(max_non_watson_crick_pairs=0),
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
    hit = evaluate_foldback(_request(case, max_non_watson_crick_pairs=0))

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
