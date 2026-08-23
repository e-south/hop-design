from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import hop_design as hop
import hop_design.discovery as discovery

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "basal" / "candidate-search-v1.json"


def _constraints(**overrides: object) -> hop.BasalConstraintProfile:
    values: dict[str, object] = {
        "require_terminal_watson_crick": True,
        "allow_active_gt_wobble": True,
        "max_active_hard_mismatches": 2,
        "max_active_non_watson_crick_pairs": 2,
        "forbid_active_middle_double_hard": True,
        "minimum_active_pair_support_index": 2.0,
        "maximum_active_pair_disruption_index": 2.5,
        "require_outer_hard_for_active_double": True,
        "reject_compact_profiles": ("MMMM",),
        "reserve_compact_profiles": (),
    }
    values.update(overrides)
    return hop.BasalConstraintProfile.model_validate(values)


def _request(
    *,
    left_arm_template: str = "AAAA",
    right_arm_template: str = "TNNT",
    acceptance: str = "active_only",
) -> discovery.BasalCandidateSearchRequest:
    return discovery.BasalCandidateSearchRequest(
        left_arm_template=left_arm_template,
        right_arm_template=right_arm_template,
        constraints=_constraints(),
        acceptance=acceptance,
    )


def test_basal_candidate_search_matches_sanitized_predecessor_set() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    result = discovery.search_basal_candidates(
        _request(
            left_arm_template=fixture["left_arm_template"],
            right_arm_template=fixture["right_arm_template"],
        ),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=16, max_hits=16),
    )

    assert result.status == "complete"
    assert result.candidate_space_size == fixture["candidate_space_size"]
    assert result.search_nodes_examined == fixture["candidate_space_size"]
    assert result.observed_hit_count == len(fixture["active"])
    assert [
        {
            "left_arm": candidate.pairing.left_arm,
            "right_arm": candidate.pairing.right_arm,
            "compact_profile": candidate.evaluation.profile.compact_profile_s3_s2_s1_s0,
        }
        for candidate in result.hits
    ] == fixture["active"]
    assert [summary.model_dump(mode="json") for summary in result.excluded] == fixture["excluded"]
    assert [candidate.canonical_ordinal for candidate in result.hits] == list(range(1, 7))
    assert all(
        candidate.candidate_id.startswith("hop:basal-candidate/")
        and len(candidate.candidate_id.removeprefix("hop:basal-candidate/").removesuffix("@1"))
        == 64
        for candidate in result.hits
    )


def test_basal_candidate_search_can_include_reserve_without_admitting_rejects() -> None:
    result = discovery.search_basal_candidates(
        _request(acceptance="allow_reserve"),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=16, max_hits=16),
    )

    assert result.status == "complete"
    assert result.observed_hit_count == 15
    assert {candidate.evaluation.decision.status for candidate in result.hits} == {
        "active",
        "reserve",
    }
    assert [summary.model_dump(mode="json") for summary in result.excluded] == [
        {
            "status": "reject",
            "reason": "explicitly_rejected_profile",
            "count": 1,
        }
    ]


def test_basal_candidate_search_reports_node_and_hit_truncation_separately() -> None:
    node_limited = discovery.search_basal_candidates(
        _request(),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=5, max_hits=16),
    )
    hit_limited = discovery.search_basal_candidates(
        _request(),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=16, max_hits=2),
    )

    assert node_limited.status == "truncated"
    assert node_limited.search_nodes_examined == 5
    assert node_limited.observed_hit_count == 1
    assert node_limited.truncated_by == ("max_search_nodes",)
    assert hit_limited.status == "truncated"
    assert hit_limited.search_nodes_examined == 16
    assert hit_limited.observed_hit_count == 6
    assert len(hit_limited.hits) == 2
    assert hit_limited.truncated_by == ("max_hits",)


def test_hit_budget_uses_content_order_not_pairing_preference() -> None:
    result = discovery.search_basal_candidates(
        _request(
            right_arm_template="NNNT",
        ).model_copy(
            update={
                "constraints": _constraints(
                    require_terminal_watson_crick=True,
                    max_active_hard_mismatches=4,
                    max_active_non_watson_crick_pairs=4,
                    forbid_active_middle_double_hard=False,
                    minimum_active_pair_support_index=0.0,
                    maximum_active_pair_disruption_index=4.0,
                    require_outer_hard_for_active_double=False,
                    reject_compact_profiles=(),
                )
            }
        ),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=64, max_hits=2),
    )

    assert [candidate.pairing.right_arm for candidate in result.hits] == ["TAAT", "TACT"]


def test_basal_candidate_search_reports_complete_infeasibility() -> None:
    result = discovery.search_basal_candidates(
        _request(right_arm_template="TTTT"),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=1, max_hits=1),
    )

    assert result.status == "infeasible"
    assert result.candidate_space_size == 1
    assert result.search_nodes_examined == 1
    assert result.observed_hit_count == 0
    assert result.hits == ()
    assert result.excluded[0].status == "reject"


def test_basal_candidate_contracts_reject_projection_and_accounting_drift() -> None:
    result = discovery.search_basal_candidates(
        _request(),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=16, max_hits=16),
    )
    candidate_data = result.hits[0].model_dump(mode="json")
    candidate_data["pairing"]["left_arm"] = "CCCC"
    with pytest.raises(ValidationError, match="pairing must equal"):
        discovery.BasalCandidate.model_validate_json(json.dumps(candidate_data))

    candidate_data = result.hits[0].model_dump(mode="json")
    candidate_data["candidate_id"] = "hop:basal-candidate/" + "0" * 64 + "@1"
    with pytest.raises(ValidationError, match="candidate_id"):
        discovery.BasalCandidate.model_validate_json(json.dumps(candidate_data))

    candidate_data = result.hits[0].model_dump(mode="json")
    candidate_data["rank"] = candidate_data.pop("canonical_ordinal")
    with pytest.raises(ValidationError):
        discovery.BasalCandidate.model_validate_json(json.dumps(candidate_data))

    result_data = result.model_dump(mode="json")
    result_data["hits"] = list(reversed(result_data["hits"]))
    for canonical_ordinal, candidate in enumerate(result_data["hits"], start=1):
        candidate["canonical_ordinal"] = canonical_ordinal
    with pytest.raises(ValidationError, match="canonical content order"):
        discovery.BasalCandidateSearchResult.model_validate_json(json.dumps(result_data))

    result_data = result.model_dump(mode="json")
    result_data["excluded"][0]["count"] += 1
    with pytest.raises(ValidationError, match="Excluded candidate counts"):
        discovery.BasalCandidateSearchResult.model_validate_json(json.dumps(result_data))


def test_basal_candidate_request_is_strict_and_normalizes_iupac_domains() -> None:
    request = _request(left_arm_template="aaaa", right_arm_template="tnnt")
    assert request.schema_id == "hop.basal-candidate-search/v2"
    assert request.left_arm_template == "AAAA"
    assert request.right_arm_template == "TNNT"

    with pytest.raises(ValidationError, match="four nucleotides"):
        _request(left_arm_template="AAA")
    with pytest.raises(ValidationError):
        discovery.BasalCandidateSearchRequest.model_validate(
            {
                **request.model_dump(mode="json"),
                "unexpected_policy": "hidden",
            }
        )

    retired = request.model_dump(mode="json", by_alias=True)
    retired["schema"] = "hop.basal-candidate-search/v1"
    with pytest.raises(ValidationError):
        discovery.BasalCandidateSearchRequest.model_validate(retired)


def test_basal_candidate_result_rejects_cardinality_and_domain_drift() -> None:
    result = discovery.search_basal_candidates(
        _request(),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=16, max_hits=16),
    )
    cardinality_data = result.model_dump(mode="json")
    cardinality_data["candidate_space_size"] += 1
    with pytest.raises(ValidationError, match="candidate_space_size"):
        discovery.BasalCandidateSearchResult.model_validate_json(json.dumps(cardinality_data))

    domain_data = result.model_dump(mode="json")
    domain_data["request"]["right_arm_template"] = "ANNA"
    with pytest.raises(ValidationError, match="outside its caller-authored domain"):
        discovery.BasalCandidateSearchResult.model_validate_json(json.dumps(domain_data))


def test_basal_candidate_result_rejects_unforced_early_stops() -> None:
    result = discovery.search_basal_candidates(
        _request(),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=16, max_hits=16),
    )
    node_data = result.model_dump(mode="json")
    node_data["search_nodes_examined"] = 15
    node_data["excluded"][1]["count"] = 8
    node_data["truncated_by"] = ["max_search_nodes"]
    node_data["status"] = "truncated"
    with pytest.raises(ValidationError, match="exhaust the available node budget"):
        discovery.BasalCandidateSearchResult.model_validate_json(json.dumps(node_data))

    hit_data = result.model_dump(mode="json")
    hit_data["hits"] = hit_data["hits"][:5]
    hit_data["truncated_by"] = ["max_hits"]
    hit_data["status"] = "truncated"
    with pytest.raises(ValidationError, match="exhaust the available hit budget"):
        discovery.BasalCandidateSearchResult.model_validate_json(json.dumps(hit_data))


def test_basal_candidate_result_rejects_duplicate_exclusion_summaries() -> None:
    result = discovery.search_basal_candidates(
        _request(),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=16, max_hits=16),
    )
    data = result.model_dump(mode="json")
    reserve = next(summary for summary in data["excluded"] if summary["status"] == "reserve")
    reserve["count"] = 4
    data["excluded"].append({**reserve, "count": 5})

    with pytest.raises(ValidationError, match="must be unique"):
        discovery.BasalCandidateSearchResult.model_validate_json(json.dumps(data))


def test_basal_candidate_contract_rejects_retired_pairing_policy_input() -> None:
    result = discovery.search_basal_candidates(
        _request(left_arm_template="AGTG", right_arm_template="CATT"),
        limits=discovery.BasalCandidateSearchLimits(max_search_nodes=1, max_hits=1),
    )
    data = result.hits[0].model_dump(mode="json")
    data["pairing"]["allow_gt_wobble"] = False

    with pytest.raises(ValidationError, match="Extra inputs"):
        discovery.BasalCandidate.model_validate_json(json.dumps(data))


def test_basal_exclusion_summary_rejects_impossible_status_reason_pair() -> None:
    with pytest.raises(ValidationError, match="status and reason"):
        discovery.BasalCandidateExclusionSummary.model_validate_json(
            json.dumps(
                {
                    "status": "reserve",
                    "reason": "active_profile",
                    "count": 1,
                }
            )
        )
