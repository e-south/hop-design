from __future__ import annotations

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.models.spec import HopSpec


def test_sequence_convenience_expands_to_an_explicit_exact_spec() -> None:
    spec = hop.create_spec(sequence="acgt", design_id="demo-exact")

    assert spec.schema_id == "hop.design/v1"
    assert spec.payload.kind == "exact"
    assert spec.payload.sequence == "ACGT"
    assert spec.junction.foldback.ref == "hop:foldback-junction/generic-gtttc@1"
    assert spec.junction.basal.ref == "hop:basal-junction/generic-g-c@1"
    assert spec.processing_route_ref == "hop:processing-route/generic-direct-synthesis@1"
    assert spec.constraint_profile_ref == "hop:constraint-profile/generic-cloneable@1"
    assert spec.defaults_ref == "hop:defaults/generic-direct-synthesis@1"
    assert spec.constraints.max_candidates == 1


def test_sequence_convenience_preserves_symbolic_degenerate_payload() -> None:
    spec = hop.create_spec(sequence="nry", design_id="demo-symbolic")

    assert spec.payload.kind == "degenerate"
    assert spec.payload.sequence == "NRY"
    assert spec.payload.paired_sequence == "RYN"
    assert "paired_sequence" not in spec.payload.model_dump()


def test_spec_rejects_a_stale_schema() -> None:
    data = hop.create_spec(sequence="ACGT", design_id="demo").model_dump(mode="json", by_alias=True)
    data["schema"] = "hop.design/v0"

    with pytest.raises(ValidationError, match=r"hop\.design/v1"):
        HopSpec.model_validate(data)


def test_spec_rejects_unknown_fields() -> None:
    data = hop.create_spec(sequence="ACGT", design_id="demo").model_dump(mode="json", by_alias=True)
    data["paired_payload"] = "ACGT"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        HopSpec.model_validate(data)


def test_spec_requires_a_bounded_candidate_count() -> None:
    data = hop.create_spec(sequence="ACGT", design_id="demo").model_dump(mode="json", by_alias=True)
    data["constraints"]["max_candidates"] = 0

    with pytest.raises(ValidationError):
        HopSpec.model_validate(data)
