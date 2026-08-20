from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

import hop_design as hop


def _foldback_option(option_id: str, *, arm: str, max_mismatches: int) -> hop.FoldbackOption:
    return hop.FoldbackOption(
        option_id=option_id,
        request=hop.FoldbackEvaluationRequest(
            precursor_sequence="CCTCAGCA",
            nick_boundary=hop.Boundary(offset=2),
            retained_tract_span=hop.Span(
                start=hop.Boundary(offset=2),
                end=hop.Boundary(offset=6),
            ),
            protected_region=hop.Span(
                start=hop.Boundary(offset=0),
                end=hop.Boundary(offset=2),
            ),
            turn_extension="T",
            foldback_arm=arm,
            constraints=hop.FoldbackConstraints(
                max_mismatches=max_mismatches,
                terminal_paired_bp_min=0,
                terminal_paired_bp_max=4,
                max_uninterrupted_paired_bp=4,
                max_added_nt=5,
                required_turn_nt=3,
                allow_protected_region_mismatches=False,
            ),
        ),
    )


def _basal_option() -> hop.BasalOption:
    return hop.BasalOption(
        option_id="basal-a",
        request=hop.BasalDesignRequest(
            pairing=hop.BasalPairingRequest(
                left_arm="AAAA",
                right_arm="TTTT",
                allow_gt_wobble=True,
            ),
            constraints=hop.BasalConstraintProfile(
                require_terminal_watson_crick=True,
                max_active_hard_mismatches=0,
                max_active_non_watson_crick_pairs=0,
                forbid_active_middle_double_hard=True,
                minimum_active_support=4.0,
                maximum_active_disruption=0.0,
                require_outer_hard_for_active_double=True,
                reject_compact_profiles=(),
                reserve_compact_profiles=(),
            ),
            acceptance="active_only",
            terminal_nick=hop.NickEvent(boundary=hop.Boundary(offset=4), strand=hop.Strand.TOP),
        ),
    )


def _space(*, max_designs: int) -> hop.ResolvedDesignSpace:
    payloads = hop.collect_payloads(
        (
            hop.PayloadRecord(record_id="payload-a", payload=hop.ExactPayload(sequence="AC")),
            hop.PayloadRecord(
                record_id="payload-b",
                payload=hop.DegeneratePayload(sequence="NR"),
            ),
        ),
        duplicate_policy=hop.DuplicateSequencePolicy.FAIL,
    )
    return hop.ResolvedDesignSpace(
        space_id="example-space",
        payloads=payloads,
        foldbacks=(
            _foldback_option("foldback-a", arm="CTGA", max_mismatches=0),
            _foldback_option("foldback-b", arm="CTAA", max_mismatches=1),
        ),
        basals=(_basal_option(),),
        releases=(hop.ReleaseOption(option_id="no-release", request=None),),
        defaults_ref="example:defaults/resolved@1",
        catalog_ref="example:processing-catalog/synthetic@1",
        constraint_profile_ref="example:constraint-profile/explicit@1",
        processing_route_ref="example:processing-route/resolved-events@1",
        per_design_constraints=hop.DesignLimits(max_candidates=1),
        limits=hop.DesignSpaceLimits(max_designs=max_designs),
        duplicate_final_sequence_policy=hop.DuplicateDesignSequencePolicy.FAIL,
    )


def test_design_space_checks_cartesian_cardinality_before_row_allocation() -> None:
    with pytest.raises(hop.DesignSpaceBudgetExceededError) as captured:
        hop.plan_design_space(_space(max_designs=3))

    assert captured.value.cardinality == 4
    assert captured.value.max_designs == 3


def test_design_space_plan_is_deterministic_typed_and_renderer_free() -> None:
    space = _space(max_designs=4)

    first = hop.plan_design_space(space)
    second = hop.plan_design_space(space)

    assert first == second
    assert first.cardinality == 4
    assert first.feasible_count == 4
    assert first.infeasible_count == 0
    assert first.duplicate_final_sequence_count == 0
    assert [
        (row.payload_record_id, row.foldback_option_id, row.basal_option_id) for row in first.rows
    ] == [
        ("payload-a", "foldback-a", "basal-a"),
        ("payload-a", "foldback-b", "basal-a"),
        ("payload-b", "foldback-a", "basal-a"),
        ("payload-b", "foldback-b", "basal-a"),
    ]
    assert len({row.spec.design_id for row in first.rows}) == 4
    assert all(row.spec.schema_id == "hop.resolved-design/v1" for row in first.rows)
    assert all(row.release_option_id == "no-release" for row in first.rows)


def test_design_space_rejects_duplicate_axis_ids() -> None:
    space = _space(max_designs=4).model_dump(mode="json", by_alias=True)
    space["foldbacks"][1]["option_id"] = "foldback-a"

    with pytest.raises(ValidationError, match="Foldback option ids must be unique"):
        hop.ResolvedDesignSpace.model_validate_json(json.dumps(space))


def test_design_space_duplicate_final_sequences_require_explicit_keep_policy() -> None:
    raw = _space(max_designs=4).model_dump(mode="json", by_alias=True)
    raw["foldbacks"][1]["request"] = raw["foldbacks"][0]["request"]

    failing = hop.ResolvedDesignSpace.model_validate_json(json.dumps(raw))
    with pytest.raises(hop.DuplicateDesignSequenceError) as captured:
        hop.plan_design_space(failing)
    assert captured.value.sequence == "AAAAACTCAGCATCTGAGTTTTT"

    raw["duplicate_final_sequence_policy"] = "keep"
    kept = hop.plan_design_space(hop.ResolvedDesignSpace.model_validate_json(json.dumps(raw)))
    assert kept.cardinality == 4
    assert kept.duplicate_final_sequence_count == 2
