"""Rejected preparations retain the exact authored constraint and observed bound."""

import copy
import csv
import io
import json

import pytest

from hop_design import construction
from tests.integration.test_request_execution import hairpin_request


def test_public_failure_reports_primer_request_and_available_span(tmp_path):
    path = hairpin_request(tmp_path)
    authored = json.loads(path.read_text())
    authored["materialization"]["source_preparation"]["forward_primer"]["annealing_length_nt"] = 20
    path.write_text(json.dumps(authored))
    receipt = construction.execute_construction_request(
        path, design_id="primer-span-diagnostic", continuation="sole-witness"
    )
    receipt.write(tmp_path / "outcome")
    bundle = construction.load_verified_construction_bundle(tmp_path / "outcome/construction")
    projection = construction.project_complete_construction_summary(bundle)
    data = json.loads(projection.json_bytes)
    (row,) = data["rows"]
    assert row["rejection_reason"] == "source-preparation-incompatible"
    diagnostic = row["preparation_constraint"]
    assert diagnostic == {
        "code": "primer-annealing-span-exceeded",
        "stage": "source-duplex-preparation",
        "field": "materialization.source_preparation.forward_primer.annealing_length_nt",
        "requirement": "at-most",
        "requested": 20,
        "available": 10,
        "message": "Source primer annealing must remain outside the payload.",
    }
    assert data["accounting"]["valid_realizations"] == 0
    assert not (tmp_path / "outcome/handoff").exists()
    (csv_row,) = list(csv.DictReader(io.StringIO(projection.csv_bytes.decode())))
    assert json.loads(csv_row["preparation_constraint_json"]) == diagnostic

    # Even a newly sealed, structurally valid claim cannot invent another bound.
    from hop_design.models.construction.complete import ConstructionSpaceResult
    from hop_design.models.construction.complete.authority import CompositionDisposition

    authority = json.loads(bundle.report_json())["result"]
    altered = copy.deepcopy(authority)
    altered["combination_dispositions"][0]["preparation_constraint"]["available"] = 9
    parsed = ConstructionSpaceResult.model_construct(
        **{
            **ConstructionSpaceResult.model_validate_json(json.dumps(authority)).__dict__,
            "combination_dispositions": tuple(
                CompositionDisposition.model_validate_json(json.dumps(item))
                for item in altered["combination_dispositions"]
            ),
        }
    )
    altered["result_id"] = parsed._expected_result_id()
    assert altered["result_id"] != authority["result_id"]
    with pytest.raises(ValueError, match="constraint diagnostic must equal"):
        ConstructionSpaceResult.model_validate_json(json.dumps(altered))


def test_fixed_adapter_lock_failure_exposes_authored_and_required_sequence(tmp_path):
    from tests.integration.test_request_execution import request_path

    path = request_path(tmp_path)
    baseline = construction.execute_construction_request(
        path, design_id="adapter-baseline", continuation="sole-witness"
    )
    baseline.write(tmp_path / "baseline")
    with (tmp_path / "baseline/handoff/oligos.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    (adapter,) = [row for row in rows if "adapter" in row["roles"]]
    authored = json.loads(path.read_text())
    authored["ends"]["right"]["cohesive_end_sequence"] = "GATC"
    geometry = authored["basal"]["geometry"]
    geometry["max_noncanonical_pairs"] = 4
    for contact in geometry["pairing_constraints"]:
        if 6 <= contact["position_from_ligation"] < 10:
            contact["allowed_class"] = "any"
    authored["materialization"]["endpoint_auxiliaries"]["adapter"] = {
        "mode": "fixed",
        "material": {
            key: adapter[key] for key in ("sequence_5prime", "five_prime_end", "three_prime_end")
        },
    }
    path.write_text(json.dumps(authored))
    receipt = construction.execute_construction_request(
        path, design_id="adapter-lock", continuation="sole-witness"
    )
    receipt.write(tmp_path / "locked")
    bundle = construction.load_verified_construction_bundle(tmp_path / "locked/construction")
    data = json.loads(construction.project_complete_construction_summary(bundle).json_bytes)
    (row,) = data["rows"]
    assert row["rejection_reason"] == "pcr-adapter-mismatch"
    diagnostic = row["preparation_constraint"]
    assert diagnostic["code"] == "fixed-adapter-sequence-mismatch"
    assert diagnostic["stage"] == "endpoint-auxiliary-preparation"
    assert (
        diagnostic["field"]
        == "materialization.endpoint_auxiliaries.adapter.material.sequence_5prime"
    )
    assert diagnostic["requested"] == adapter["sequence_5prime"]
    assert diagnostic["requirement"] == "starts-with"
    assert len(diagnostic["available"]) == 17
    assert len(diagnostic["requested"]) == 31
    # This request changes the two adapter bases independently established in
    # the public sticky-end example; the original material remains locked.
    changed = [
        i
        for i, (a, b) in enumerate(
            zip(diagnostic["requested"][:17], diagnostic["available"], strict=True)
        )
        if a != b
    ]
    assert changed == [8, 9]
    assert data["accounting"]["valid_realizations"] == 0
    assert not (tmp_path / "locked/handoff").exists()
