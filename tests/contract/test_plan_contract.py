from __future__ import annotations

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


def test_plan_rejects_source_and_final_insert_drift() -> None:
    def change(data: dict[str, object]) -> None:
        source = data["source_oligo"]
        assert isinstance(source, dict)
        source["sequence"] = "AAAA"

    _reject_plan_change(change, "source oligo and final insert equality")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("processing_route_ref", "hop:processing-route/other@1", "route and lock"),
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
        features = data["features"]
        assert isinstance(features, list)
        features[0], features[1] = features[1], features[0]

    _reject_plan_change(reorder, "declared generic-route order")

    def create_gap(data: dict[str, object]) -> None:
        features = data["features"]
        assert isinstance(features, list)
        second = features[1]
        assert isinstance(second, dict)
        span = second["span"]
        assert isinstance(span, dict)
        start = span["start"]
        assert isinstance(start, dict)
        start["offset"] = 2

    _reject_plan_change(create_gap, "contiguous and ordered")


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
