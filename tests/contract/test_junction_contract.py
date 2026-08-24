from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.catalog.defaults import generic_catalog_junction_derivation
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import (
    BasalJunction,
    FoldbackJunction,
    JunctionPairKind,
    JunctionPairObservation,
)


def test_generic_route_uses_canonical_junction_terms_and_valid_geometry() -> None:
    route = generic_catalog_junction_derivation()

    assert route.foldback_junction.sequence == "GTTTC"
    assert route.foldback_junction.retained_tract_span == Span(
        start=Boundary(offset=0), end=Boundary(offset=1)
    )
    assert route.foldback_junction.turn_span == Span(
        start=Boundary(offset=1), end=Boundary(offset=4)
    )
    assert route.foldback_junction.foldback_arm_span == Span(
        start=Boundary(offset=4), end=Boundary(offset=5)
    )
    assert route.basal_junction.left_arm == "G"
    assert route.basal_junction.right_arm == "C"
    assert route.basal_junction.pair_count.value == 1


def test_foldback_junction_requires_contiguous_partitioning() -> None:
    route = generic_catalog_junction_derivation()
    junction = route.foldback_junction

    with pytest.raises(ValidationError, match="partition"):
        FoldbackJunction(
            junction_id=junction.junction_id,
            sequence=junction.sequence,
            retained_tract_span=junction.retained_tract_span,
            turn_span=Span(start=Boundary(offset=2), end=Boundary(offset=4)),
            foldback_arm_span=junction.foldback_arm_span,
            pairs=junction.pairs,
        )


def test_basal_junction_pair_bases_must_match_the_declared_arms() -> None:
    data = generic_catalog_junction_derivation().basal_junction.model_dump()
    data["right_arm"] = "A"

    with pytest.raises(ValidationError, match="pair bases"):
        type(generic_catalog_junction_derivation().basal_junction).model_validate(data)


def test_basal_junction_can_represent_non_watson_crick_pair_calls() -> None:
    evaluation = hop.evaluate_basal_pairing(
        hop.BasalPairingRequest(
            left_arm="AAAA",
            right_arm="TGGT",
        ),
        constraints=hop.BasalConstraintProfile(
            require_terminal_watson_crick=True,
            allow_active_gt_wobble=True,
            max_active_hard_mismatches=4,
            max_active_non_watson_crick_pairs=4,
            forbid_active_middle_double_hard=False,
            minimum_active_pair_support_index=0.0,
            maximum_active_pair_disruption_index=4.0,
            require_outer_hard_for_active_double=False,
            reject_compact_profiles=(),
            reserve_compact_profiles=(),
        ),
    )

    assert [pair.kind for pair in evaluation.junction.pairs] == [
        "watson_crick",
        "hard_mismatch",
        "hard_mismatch",
        "watson_crick",
    ]


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {
                "left_index": 0,
                "right_index": 0,
                "left_base": "A",
                "right_base": "A",
                "kind": "watson_crick",
            },
            "Watson-Crick",
        ),
        (
            {
                "left_index": 0,
                "right_index": 0,
                "left_base": "A",
                "right_base": "C",
                "kind": "gt_wobble",
            },
            "G:T wobble",
        ),
        (
            {
                "left_index": 0,
                "right_index": 0,
                "left_base": "A",
                "right_base": "T",
                "kind": "hard_mismatch",
            },
            "Hard-mismatch",
        ),
        (
            {
                "left_index": 0,
                "right_index": 0,
                "left_base": "G",
                "right_base": "T",
                "kind": "hard_mismatch",
            },
            "G:T wobble",
        ),
        (
            {
                "left_index": 0,
                "right_index": 0,
                "left_base": "AA",
                "right_base": "T",
                "kind": "watson_crick",
            },
            "exactly one",
        ),
    ],
)
def test_pair_observation_rejects_false_physical_calls(
    values: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        JunctionPairObservation.model_validate_json(json.dumps(values))


def test_pair_observation_exposes_display_alignment_and_match_state() -> None:
    pair = JunctionPairObservation(
        left_index=0,
        right_index=0,
        left_base="G",
        right_base="C",
        kind=JunctionPairKind.WATSON_CRICK,
    )

    assert pair.aligned_right_base == "G"
    assert pair.is_match


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("pairs.0.right_index", 3, "outside foldback arm"),
        ("pairs.0.left_base", "A", "pair bases"),
    ],
)
def test_foldback_junction_rejects_pair_geometry_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    data = generic_catalog_junction_derivation().foldback_junction.model_dump(mode="json")
    _, index, key = field.split(".")
    data["pairs"][int(index)][key] = value
    if key == "left_base":
        data["pairs"][int(index)]["kind"] = "hard_mismatch"

    with pytest.raises(ValidationError, match=message):
        FoldbackJunction.model_validate_json(json.dumps(data))


def test_junction_sequences_reject_non_string_values() -> None:
    foldback_data = generic_catalog_junction_derivation().foldback_junction.model_dump()
    foldback_data["sequence"] = 42
    with pytest.raises(ValidationError, match="must be a string"):
        FoldbackJunction.model_validate(foldback_data)

    basal_data = generic_catalog_junction_derivation().basal_junction.model_dump()
    basal_data["left_arm"] = 42
    with pytest.raises(ValidationError, match="must be a string"):
        BasalJunction.model_validate(basal_data)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("pair_count", {"value": 2}, "pair count"),
        ("pairs", (), "at least 1"),
    ],
)
def test_basal_junction_rejects_inconsistent_geometry(
    field: str,
    value: object,
    message: str,
) -> None:
    data = generic_catalog_junction_derivation().basal_junction.model_dump(mode="json")
    data[field] = value

    with pytest.raises(ValidationError, match=message):
        BasalJunction.model_validate_json(json.dumps(data))
