"""An adapter-ligated hairpin is independently obtainable without a later duplex."""

import csv
import json

import pytest

from hop_design import construction
from tests.integration.test_request_execution import request_path


def adapter_request(tmp_path):
    path = request_path(tmp_path)
    request = json.loads(path.read_bytes())
    request.update(endpoint="adapter_ligated_hairpin", ends=None, release=None)
    auxiliaries = request["materialization"].pop("endpoint_auxiliaries")
    request["materialization"]["adapter_ligation"] = auxiliaries["adapter"]
    path.write_text(json.dumps(request))
    return path


def test_hairpin_endpoint_stops_before_copying_and_release(tmp_path):
    packet = construction.execute_construction_request(
        adapter_request(tmp_path),
        design_id="adapter-endpoint",
        continuation="sole-witness",
    )
    output = packet.write(tmp_path / "hairpin")
    assert json.loads(packet.json_bytes)["status"] == "complete"
    receipt = construction.load_verified_construction_bundle(output / "construction")
    portrait = construction.project_hairpin_portrait(
        receipt,
        materialized_realization_id=receipt.materialized_realization_ids[0],
    )
    molecule = json.loads(portrait.json_bytes)
    assert molecule["stage_role"] == "endpoint"
    assert molecule["endpoint"] == "adapter_ligated_hairpin"
    assert molecule["state"]["phase"] == "adapter_ligated"
    assert molecule["later_release"] is None
    assert len(molecule["join_boundaries"]) == 2
    rows = list(csv.DictReader((output / "handoff/oligos.csv").open()))
    assert len(rows) == 4
    report = (output / "handoff/report.md").read_text()
    assert "adapter-ligated hairpin" in report.lower()
    assert "endpoint forward primer" not in report.lower()


def test_irrelevant_downstream_primer_failure_does_not_block_hairpin(tmp_path):
    path = request_path(tmp_path)
    request = json.loads(path.read_bytes())
    request.update(endpoint="hairpin_pcr_duplex", ends=None, release=None)
    request["materialization"]["endpoint_auxiliaries"]["forward_primer"] = {
        "mode": "derive",
        "annealing_length_nt": 1000,
    }
    path.write_text(json.dumps(request))
    copied = construction.execute_construction_request(
        path, design_id="copy-fails", continuation="sole-witness"
    )
    outcome = json.loads(copied.json_bytes)
    assert outcome["status"] == "infeasible"
    assert outcome["rejection_reasons"] == ["pcr-primer-mismatch"]
    request["endpoint"] = "adapter_ligated_hairpin"
    policy = request["materialization"].pop("endpoint_auxiliaries")
    request["materialization"]["adapter_ligation"] = policy["adapter"]
    path.write_text(json.dumps(request))
    joined = construction.execute_construction_request(
        path, design_id="hairpin-completes", continuation="sole-witness"
    )
    assert json.loads(joined.json_bytes)["status"] == "complete"


@pytest.mark.parametrize("change", ["missing-adapter", "downstream-primers", "release"])
def test_hairpin_request_rejects_inappropriate_materials_and_release(tmp_path, change):
    path = adapter_request(tmp_path)
    request = json.loads(path.read_bytes())
    reference = json.loads(request_path(tmp_path).read_bytes())
    if change == "missing-adapter":
        request["materialization"].pop("adapter_ligation")
    elif change == "downstream-primers":
        request["materialization"]["endpoint_auxiliaries"] = reference["materialization"][
            "endpoint_auxiliaries"
        ]
    else:
        request["ends"], request["release"] = reference["ends"], reference["release"]
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        construction.prepare_construction_request(path)


def test_fixed_hairpin_adapter_cannot_receive_redesign_permission(tmp_path):
    product = json.loads(adapter_request(tmp_path).read_bytes())
    product["materialization"]["adapter_ligation"] = {
        "mode": "fixed",
        "material": {
            "sequence_5prime": "ACGTACGTACGTACGTACGT",
            "five_prime_end": "phosphate",
            "three_prime_end": "hydroxyl",
        },
    }
    path = tmp_path / "discovery.json"
    path.write_text(
        json.dumps(
            {
                "schema": "hop.scaffold-discovery/v1",
                "product": product,
                "scaffold": {"open_side_paired_positions": {"minimum": 18, "maximum": 18}},
                "preparation_changes": {"adapter_redesign": "allow"},
                "comparison_stage": "endpoint",
                "max_branches": 1,
                "max_continuations_per_branch": 1,
            }
        )
    )
    packet = construction.prepare_scaffold_discovery(path)
    preview = json.loads(packet.json_bytes)
    assert preview["status"] == "conflicting_requirements"
    assert preview["material_policies"]["ligation_adapter"] == "fixed"
    assert preview["conflicts"][0]["inherited_field"] == "product.materialization.adapter_ligation"


def test_truncated_adapter_chronology_fails_with_a_validation_error(tmp_path):
    from hop_design.models.construction.complete.adapter.validation import (
        validate_adapter_realization,
    )

    packet = construction.execute_construction_request(
        adapter_request(tmp_path), design_id="truncated-prefix", continuation="sole-witness"
    )
    output = packet.write(tmp_path / "complete")
    receipt = construction.load_verified_construction_bundle(output / "construction")
    route = receipt._verified_source().result.realizations[0]
    short = route.model_copy(
        update={
            "construction_program": route.construction_program.model_copy(
                update={"states": route.construction_program.states[:2]}
            )
        }
    )
    with pytest.raises(ValueError, match="exact source-to-ligation phases"):
        validate_adapter_realization(short)


def test_failed_release_can_be_replaced_by_an_independent_hairpin_request(tmp_path):
    from tests.integration.test_scaffold_discovery import method_request

    discovery = method_request(tmp_path)
    branches = json.loads(construction.prepare_scaffold_discovery(discovery).json_bytes)["branches"]
    product = next(
        b["request"] for b in branches if b["release_enzyme_id"] == "example:enzyme/bbsi-hf@1"
    )
    product["foldback"]["geometry"]["loop_lengths_nt"] = [3]
    path = tmp_path / "product.json"
    path.write_text(json.dumps(product))
    released = construction.execute_construction_request(
        path, design_id="release-fails", continuation="sole-witness"
    )
    failure = json.loads(released.json_bytes)
    assert failure["status"] == "infeasible"
    assert failure["rejection_reasons"] == ["clone-end-generation-incompatible"]
    product.update(endpoint="adapter_ligated_hairpin", ends=None, release=None)
    auxiliaries = product["materialization"].pop("endpoint_auxiliaries")
    product["materialization"]["adapter_ligation"] = auxiliaries["adapter"]
    path.write_text(json.dumps(product))
    hairpin = construction.execute_construction_request(
        path, design_id="stop-at-hairpin", continuation="sole-witness"
    )
    assert json.loads(hairpin.json_bytes)["status"] == "complete"
