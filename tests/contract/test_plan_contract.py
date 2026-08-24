from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.models.plan import HopPlan, SequenceFeature, SequenceRecord


def _reject_plan_change(change: Callable[[dict[str, object]], None], message: str) -> None:
    data = hop.compile(sequence="ACGT", design_id="demo").plan.model_dump(
        mode="json", by_alias=True
    )
    change(data)
    with pytest.raises(ValidationError, match=message):
        HopPlan.model_validate_json(json.dumps(data))


def test_plan_rejects_independently_authored_paired_payload() -> None:
    _reject_plan_change(
        lambda data: data.__setitem__("paired_payload_sequence", "AAAA"),
        "must be derived",
    )


def test_plan_owns_one_typed_hairpin_encoding_insert() -> None:
    plan = hop.compile(sequence="ACGT", design_id="demo").plan

    assert plan.schema_id == "hop.plan/v3"
    assert plan.design_derivation.kind == "catalog_junctions"
    assert not hasattr(plan, "processing_route")
    assert plan.hairpin_encoding_insert.kind == "hairpin_encoding_insert"
    assert plan.hairpin_encoding_insert.representation == "one_dimensional_sequence"
    assert plan.hairpin_encoding_insert.alphabet == "dna"
    assert plan.hairpin_encoding_insert.coordinate_system == "zero_based_half_open"
    assert plan.hairpin_encoding_insert.sequence_digest == (
        f"sha256:{hashlib.sha256(plan.hairpin_encoding_insert.sequence.encode()).hexdigest()}"
    )
    assert (
        "".join(feature.sequence for feature in plan.hairpin_encoding_insert.features)
        == plan.hairpin_encoding_insert.sequence
    )
    assert not hasattr(plan, "final_insert")
    assert not hasattr(plan, "features")


def test_plan_rejects_source_and_hairpin_encoding_drift() -> None:
    def change(data: dict[str, object]) -> None:
        source = data["source_oligo"]
        assert isinstance(source, dict)
        source["sequence"] = "AAAA"

    _reject_plan_change(change, "source and encoding equality")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "design_derivation_ref",
            "hop:design-derivation/other@1",
            "derivation and lock",
        ),
        ("catalog_ref", "hop:catalog/other@1", "catalog and lock"),
        ("foldback_junction_ref", "hop:foldback-junction/other@1", "foldback and lock"),
        ("basal_junction_ref", "hop:basal-junction/other@1", "basal and lock"),
    ],
)
def test_plan_rejects_route_lock_drift(field: str, value: str, message: str) -> None:
    def change(data: dict[str, object]) -> None:
        lock = data["lock"]
        assert isinstance(lock, dict)
        lock[field] = value

    _reject_plan_change(change, message)


def test_plan_rejects_feature_order_and_coordinate_gaps() -> None:
    def reorder(data: dict[str, object]) -> None:
        encoding = data["hairpin_encoding_insert"]
        assert isinstance(encoding, dict)
        features = encoding["features"]
        assert isinstance(features, list)
        features[0], features[1] = features[1], features[0]

    _reject_plan_change(reorder, "contiguous and ordered")

    def create_gap(data: dict[str, object]) -> None:
        encoding = data["hairpin_encoding_insert"]
        assert isinstance(encoding, dict)
        features = encoding["features"]
        assert isinstance(features, list)
        second = features[1]
        assert isinstance(second, dict)
        span = second["span"]
        assert isinstance(span, dict)
        start = span["start"]
        assert isinstance(start, dict)
        start["offset"] = 2

    _reject_plan_change(create_gap, "contiguous and ordered")


def test_plan_rejects_hairpin_encoding_digest_drift() -> None:
    def change(data: dict[str, object]) -> None:
        encoding = data["hairpin_encoding_insert"]
        assert isinstance(encoding, dict)
        encoding["sequence_digest"] = f"sha256:{'0' * 64}"

    _reject_plan_change(change, "digest must match")


def test_plan_sequence_records_and_features_reject_non_strings() -> None:
    with pytest.raises(ValidationError, match="must be a string"):
        SequenceRecord(record_id="record", sequence=42)  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="must be a string"):
        SequenceFeature.model_validate(
            {
                "role": "payload",
                "span": {"start": {"offset": 0}, "end": {"offset": 1}},
                "sequence": 42,
            }
        )
