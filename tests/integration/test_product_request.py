"""Preserve authored product intent while expanding existing construction contracts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.models.construction.complete.source_preparation import (
    LinearSourceMaterializationSpec,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.source import ConstructionSource

ROOT = Path(__file__).resolve().parents[2]


def _request():
    return json.loads((ROOT / "examples/complete-construction/product-request.json").read_text())


def _write(tmp_path, authored):
    path = tmp_path / "request.json"
    path.write_text(json.dumps(authored))
    return path


def test_product_lowering_reuses_the_validated_catalog_without_changing_serialization():
    product = ProductRequest.model_validate_json(json.dumps(_request()))
    before = product.model_dump_json(by_alias=True)
    source = product.construction_source()
    assert source.foldback.enzyme_provisioning.catalog is product.enzyme_catalog
    assert source.basal.enzyme_provisioning.catalog is product.enzyme_catalog
    assert source.composition.release.enzyme_provisioning.catalog is product.enzyme_catalog
    assert product.model_dump_json(by_alias=True) == before
    assert ConstructionSource.model_validate_json(source.model_dump_json(by_alias=True)) == source


@pytest.mark.parametrize("endpoint", ["hairpin", "adapter_ligated_hairpin"])
def test_earlier_endpoint_lowering_reuses_catalog_without_adding_release(endpoint):
    resolved = construction.resolve_design_request(
        {"stem_arm": _request()["stem_arm"], "product": endpoint}
    )
    product = ProductRequest.model_validate_json(
        json.dumps(json.loads(resolved.json_bytes)["effective_request"])
    )
    source = product.construction_source()
    assert source.foldback.enzyme_provisioning.catalog is product.enzyme_catalog
    if source.basal is not None:
        assert source.basal.enzyme_provisioning.catalog is product.enzyme_catalog
    assert source.composition.release is None
    assert ConstructionSource.model_validate_json(source.model_dump_json(by_alias=True)) == source


def test_product_request_cli_and_api_expand_identical_intent(tmp_path):
    authored = _request()
    path = _write(tmp_path, authored)
    prepared = construction.prepare_construction_request(path)
    api_output = prepared.write(tmp_path / "api")
    result = CliRunner().invoke(
        app, ["construction", "prepare", str(path), "--out", str(tmp_path / "cli")]
    )
    assert result.exit_code == 0, result.output
    assert (api_output / "construction.json").read_bytes() == (
        tmp_path / "cli/construction.json"
    ).read_bytes()
    expanded = json.loads(prepared.source_json_bytes)
    ConstructionSource.model_validate_json(prepared.source_json_bytes)
    for family in ("foldback", "basal"):
        assert expanded[family]["payload"]["payload"]["sequence"] == authored["stem_arm"]
        assert expanded[family]["payload"]["foldback_boundary"]["offset"] == 34
    assert expanded["composition"]["release"]["left"] == authored["ends"]["left"]
    assert expanded["composition"]["release"]["right"] == authored["ends"]["right"]
    future = expanded["basal"]["geometry_domain"]["future_release"]
    assert future == {**authored["ends"]["right"], **authored["release"]["basal_projection"]}
    materialization = LinearSourceMaterializationSpec.model_validate_json(
        json.dumps(authored["materialization"])
    ).model_dump(mode="json")
    assert expanded["composition"]["materialization"] == materialization
    assert "Required" in prepared.report_text and "Derived" in prepared.report_text
    assert "Unresolved" in prepared.report_text
    assert "not a verified construction" in prepared.report_text
    assert json.loads((api_output / "request.json").read_bytes()) == authored
    with pytest.raises(FileExistsError):
        prepared.write(api_output)


@pytest.mark.parametrize(
    "kind",
    [
        "unknown",
        "missing-end",
        "duplicate-end",
        "reserved-enzyme",
        "wrong-family",
        "missing-basal",
        "symbolic",
        "boolean-offset",
        "orientation",
        "internal-schema",
    ],
)
def test_product_request_rejects_ambiguous_or_incomplete_intent(tmp_path, kind):
    authored = _request()
    if kind == "unknown":
        authored["invented_policy"] = True
    elif kind == "missing-end":
        del authored["ends"]["left"]
    elif kind == "duplicate-end":
        authored["basal"]["geometry"]["future_release"] = {
            **authored["ends"]["right"],
            **authored["release"]["basal_projection"],
        }
    elif kind == "reserved-enzyme":
        authored["release"]["enzymes"]["reserved_enzyme_ids"] = authored["release"]["enzymes"][
            "allowed_enzyme_ids"
        ]
    elif kind == "wrong-family":
        authored["foldback"]["geometry"]["family"] = "basal"
    elif kind == "missing-basal":
        authored.pop("basal")
    elif kind == "symbolic":
        authored["stem_arm"] = "ACGN"
    elif kind == "orientation":
        authored["ends"]["right"]["orientation"] = "top"
    elif kind == "internal-schema":
        authored["enzyme_catalog"]["schema_id"] = authored["enzyme_catalog"].pop("schema")
    else:
        authored["ends"]["left"]["payload_end_offset_bp"] = True
    path = _write(tmp_path, authored)
    with pytest.raises(ValueError):
        construction.prepare_construction_request(path)
    result = CliRunner().invoke(
        app, ["construction", "prepare", str(path), "--out", str(tmp_path / "output")]
    )
    assert result.exit_code == 2
    assert not (tmp_path / "output").exists()


def test_hairpin_authoring_omits_downstream_requirements(tmp_path):
    authored = _request()
    authored.update(endpoint="ssdna_hairpin")
    for field in ("ends", "basal", "release"):
        authored.pop(field)
    authored["materialization"].pop("endpoint_auxiliaries")
    authored["materialization"]["source_preparation"]["source_ssdna"] = {
        "mode": "derive",
        "five_prime_end": "hydroxyl",
        "three_prime_end": "hydroxyl",
    }
    prepared = construction.prepare_construction_request(_write(tmp_path, authored))
    expanded = json.loads(prepared.source_json_bytes)
    assert expanded["basal"] is None
    assert expanded["composition"]["release"] is None
    assert "downstream" in prepared.report_text
    conflicting = deepcopy(authored)
    conflicting["ends"] = _request()["ends"]
    with pytest.raises(ValueError):
        construction.prepare_construction_request(_write(tmp_path, conflicting))


def test_left_end_edit_propagates_to_guaranteed_source_contacts(tmp_path):
    authored = _request()
    authored["ends"]["left"]["cohesive_end_sequence"] = "GATC"
    geometry = authored["basal"]["geometry"]
    geometry["max_noncanonical_pairs"] = 4
    for contact in geometry["pairing_constraints"]:
        if 6 <= contact["position_from_ligation"] < 10:
            contact.pop("allowed_source_bases", None)
            contact["allowed_class"] = "any"
    prepared = construction.prepare_construction_request(_write(tmp_path, authored))
    source = json.loads(prepared.source_json_bytes)
    contacts = source["basal"]["geometry_domain"]["pairing_constraints"]
    assert {
        c["position_from_ligation"]: c["allowed_source_bases"]
        for c in contacts
        if 6 <= c["position_from_ligation"] < 10
    } == {6: ["C"], 7: ["T"], 8: ["A"], 9: ["G"]}
    assert source["composition"]["release"]["right"] == authored["ends"]["right"]
    assert all(
        c["allowed_class"] == "any" for c in contacts if 6 <= c["position_from_ligation"] < 10
    )


def test_conflicting_source_base_permission_names_the_supported_conflict(tmp_path):
    authored = _request()
    authored["ends"]["left"]["cohesive_end_sequence"] = "GATC"
    authored["basal"]["geometry"]["pairing_constraints"][6]["allowed_source_bases"] = ["A"]
    with pytest.raises(ValueError, match=r"left end.*source.*position 6"):
        construction.prepare_construction_request(_write(tmp_path, authored))


@pytest.mark.parametrize("change", ["multiple-offsets", "other-strand"])
def test_unresolved_source_frame_does_not_narrow_local_base_permissions(tmp_path, change):
    authored = _request()
    if change == "multiple-offsets":
        authored["basal"]["geometry"]["nick_offsets_nt"] = [0, 2]
    else:
        authored["basal"]["geometry"]["nick_strand"] = "top"
    prepared = construction.prepare_construction_request(_write(tmp_path, authored))
    expanded = json.loads(prepared.source_json_bytes)
    contacts = expanded["basal"]["geometry_domain"]["pairing_constraints"]
    assert all(c["allowed_source_bases"] == ["A", "C", "G", "T"] for c in contacts)
    assert expanded["composition"]["release"]["left"] == authored["ends"]["left"]
    assert "No additional local source-base propagation" in prepared.report_text
