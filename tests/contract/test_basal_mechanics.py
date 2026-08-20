from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from hop_design.design.basal import evaluate_basal_pairing
from hop_design.kernel.basal import classify_basal_pairing, surviving_strand
from hop_design.models.basal import (
    BasalConstraintProfile,
    BasalEvaluation,
    BasalPairingRequest,
    BasalPolicyDecision,
)
from hop_design.models.junction import Strand

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "basal" / "pairing-v1.json"


def _policy(**overrides: object) -> BasalConstraintProfile:
    values: dict[str, object] = {
        "require_terminal_watson_crick": True,
        "max_active_hard_mismatches": 2,
        "max_active_non_watson_crick_pairs": 2,
        "forbid_active_middle_double_hard": True,
        "minimum_active_support": 2.0,
        "maximum_active_disruption": 2.5,
        "require_outer_hard_for_active_double": True,
        "reject_compact_profiles": ("MMMM",),
        "reserve_compact_profiles": (),
    }
    values.update(overrides)
    return BasalConstraintProfile.model_validate(values)


def test_basal_pairing_matches_sanitized_truth_table() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for case in fixture["reference_profiles"]:
        profile = classify_basal_pairing(
            BasalPairingRequest(
                left_arm=case["left_arm"],
                right_arm=case["right_arm"],
                allow_gt_wobble=True,
            )
        )
        assert profile.compact_profile_s3_s2_s1_s0 == case["compact_profile"]


def test_basal_pairing_exposes_physical_wobble_and_aligned_base() -> None:
    profile = classify_basal_pairing(
        BasalPairingRequest(left_arm="AGTG", right_arm="CATT", allow_gt_wobble=True)
    )

    assert [pair.site for pair in profile.pairs] == ["S3", "S2", "S1", "S0"]
    assert profile.pairs[1].left_base == "G"
    assert profile.pairs[1].right_base == "T"
    assert profile.pairs[1].aligned_right_base == "A"
    assert profile.pairs[1].kind == "gt_wobble"
    assert profile.pairs[1].compact_symbol == "W"


def test_basal_wobble_is_an_explicit_caller_choice() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["wobble_profile"]

    wobble = classify_basal_pairing(
        BasalPairingRequest(
            left_arm=fixture["left_arm"],
            right_arm=fixture["right_arm"],
            allow_gt_wobble=True,
        )
    )
    strict = classify_basal_pairing(
        BasalPairingRequest(
            left_arm=fixture["left_arm"],
            right_arm=fixture["right_arm"],
            allow_gt_wobble=False,
        )
    )

    assert wobble.compact_profile_s3_s2_s1_s0 == fixture["with_wobble"]
    assert strict.compact_profile_s3_s2_s1_s0 == fixture["without_wobble"]


def test_basal_policy_is_explicit_and_separate_from_pair_classification() -> None:
    terminal_mismatch = evaluate_basal_pairing(
        BasalPairingRequest(left_arm="AAAA", right_arm="AAAA", allow_gt_wobble=True),
        constraints=_policy(),
    )
    middle_double = evaluate_basal_pairing(
        BasalPairingRequest(left_arm="AAAA", right_arm="TGGT", allow_gt_wobble=True),
        constraints=_policy(reject_compact_profiles=()),
    )
    edge_double = evaluate_basal_pairing(
        BasalPairingRequest(left_arm="AAAA", right_arm="TTGG", allow_gt_wobble=True),
        constraints=_policy(reject_compact_profiles=()),
    )

    assert terminal_mismatch.decision.status == "reject"
    assert terminal_mismatch.decision.reason == "terminal_pair_not_watson_crick"
    assert terminal_mismatch.report.status == "infeasible"
    assert terminal_mismatch.report.diagnostics[0].code == "HOP-BASAL-001"
    assert middle_double.profile.compact_profile_s3_s2_s1_s0 == "MXXM"
    assert middle_double.decision.status == "reserve"
    assert middle_double.decision.reason == "middle_double_hard_mismatch"
    assert edge_double.profile.compact_profile_s3_s2_s1_s0 == "XXMM"
    assert edge_double.decision.status == "active"


def test_basal_policy_decision_rejects_status_reason_drift() -> None:
    with pytest.raises(ValidationError, match="status and reason"):
        BasalPolicyDecision.model_validate_json(
            json.dumps({"status": "active", "reason": "explicitly_reserved_profile"})
        )


def test_basal_evaluation_rejects_decision_report_drift() -> None:
    active = evaluate_basal_pairing(
        BasalPairingRequest(left_arm="AAAA", right_arm="TTTT", allow_gt_wobble=True),
        constraints=_policy(reject_compact_profiles=()),
    )
    reserve = evaluate_basal_pairing(
        BasalPairingRequest(left_arm="AAAA", right_arm="TTTT", allow_gt_wobble=True),
        constraints=_policy(reject_compact_profiles=(), reserve_compact_profiles=("MMMM",)),
    )
    data = active.model_dump(mode="json")
    data["report"] = reserve.report.model_dump(mode="json")

    with pytest.raises(ValidationError, match="decision and report"):
        BasalEvaluation.model_validate_json(json.dumps(data))


def test_nicked_and_surviving_strands_are_literal_opposites() -> None:
    assert surviving_strand(Strand.TOP) is Strand.BOTTOM
    assert surviving_strand(Strand.BOTTOM) is Strand.TOP


def test_basal_policy_covers_every_explicit_caller_gate() -> None:
    cases = (
        (
            "AAAA",
            "TTTT",
            _policy(),
            "reject",
            "explicitly_rejected_profile",
        ),
        (
            "AAAA",
            "TTTT",
            _policy(reject_compact_profiles=(), reserve_compact_profiles=("MMMM",)),
            "reserve",
            "explicitly_reserved_profile",
        ),
        (
            "GTGA",
            "TTGA",
            _policy(
                require_terminal_watson_crick=False,
                reject_compact_profiles=(),
                max_active_non_watson_crick_pairs=2,
            ),
            "reserve",
            "too_many_non_watson_crick_pairs",
        ),
        (
            "CGGG",
            "ACAG",
            _policy(
                require_terminal_watson_crick=False,
                reject_compact_profiles=(),
                max_active_non_watson_crick_pairs=4,
                max_active_hard_mismatches=1,
            ),
            "reserve",
            "too_many_hard_mismatches",
        ),
        (
            "CGGG",
            "ACAG",
            _policy(
                require_terminal_watson_crick=False,
                reject_compact_profiles=(),
                max_active_non_watson_crick_pairs=4,
                max_active_hard_mismatches=4,
                forbid_active_middle_double_hard=False,
                minimum_active_support=4.0,
            ),
            "reserve",
            "insufficient_support",
        ),
        (
            "CGGG",
            "ACAG",
            _policy(
                require_terminal_watson_crick=False,
                reject_compact_profiles=(),
                max_active_non_watson_crick_pairs=4,
                max_active_hard_mismatches=4,
                forbid_active_middle_double_hard=False,
                minimum_active_support=0.0,
                maximum_active_disruption=1.0,
            ),
            "reserve",
            "excessive_disruption",
        ),
        (
            "AAAA",
            "TGGT",
            _policy(
                reject_compact_profiles=(),
                max_active_non_watson_crick_pairs=4,
                max_active_hard_mismatches=4,
                forbid_active_middle_double_hard=False,
                minimum_active_support=0.0,
                maximum_active_disruption=4.0,
            ),
            "reserve",
            "double_hard_without_outer_hard_mismatch",
        ),
    )

    for left_arm, right_arm, constraints, expected_status, expected_reason in cases:
        evaluation = evaluate_basal_pairing(
            BasalPairingRequest(
                left_arm=left_arm,
                right_arm=right_arm,
                allow_gt_wobble=True,
            ),
            constraints=constraints,
        )
        assert evaluation.decision.status == expected_status
        assert evaluation.decision.reason == expected_reason
