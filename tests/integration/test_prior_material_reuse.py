"""Reusing a verified old material differs from preserving its product or a new-set agreement."""

import json
import shutil

import pytest

from hop_design import construction
from tests.integration.test_comparison_product_reference import referenced_brief
from tests.support.grouped_comparison import create_method_pool


@pytest.fixture(scope="module")
def prior_pool(tmp_path_factory):
    return create_method_pool(tmp_path_factory.mktemp("prior-materials"))


def reuse_request(tmp_path, prior_pool, method="bsmbi"):
    discovery, pool = prior_pool
    path = referenced_brief(tmp_path, discovery, pool)
    value = json.loads(path.read_bytes())
    value["schema"] = "hop.comparison-brief/v3"
    name = f"loop3-{method}"
    value["required_members"] = [m for m in value["required_members"] if m["name"] == name]
    value["groups"] = [{**value["groups"][0], "members": [name]}]
    reference = value["groups"][0]["product_reference"]
    value["reuse_prior_materials"] = {
        "reference": {k: v for k, v in reference.items() if k != "stage"},
        "roles": ["source_ssdna"],
    }
    path.write_text(json.dumps(value))
    return path


def test_prior_source_is_compiled_to_fixed_policy_and_prevents_substitution(prior_pool, tmp_path):
    path = reuse_request(tmp_path, prior_pool)
    original = path.read_bytes()
    preview = construction.prepare_scaffold_comparison(path)
    summary = json.loads(preview.json_bytes)
    assert summary["status"] == "ready"
    prior = summary["prior_material_reference"]
    assert prior["required_roles"] == ["source_ssdna"]
    for branch in summary["discovery"]["branches"]:
        policy = branch["request"]["materialization"]["source_preparation"]["source_ssdna"]
        assert policy["mode"] == "fixed"
        assert policy["material"] == prior["materials"]["source_ssdna"]
    packet = construction.execute_scaffold_comparison(path)
    result = json.loads(packet.json_bytes)
    assert result["sets"] == []
    assert result["members"][0]["status"] == "missing_from_evaluated_pool"
    assert all(
        o["materials"]["source_ssdna"]["material_id"]
        == prior["materials"]["source_ssdna"]["material_id"]
        for o in result["options"]
    )
    assert path.read_bytes() == original
    opening = dict(packet._files)["pages/comparison-1.svg"].decode()
    assert "source-preparation-incompatible" in opening
    assert "missing from the evaluated pool" in opening


def test_preserving_product_without_prior_reuse_allows_a_new_source(prior_pool, tmp_path):
    path = reuse_request(tmp_path, prior_pool)
    value = json.loads(path.read_bytes())
    value.pop("reuse_prior_materials")
    path.write_text(json.dumps(value))
    result = json.loads(construction.execute_scaffold_comparison(path).json_bytes)
    assert result["status"] == "comparison_available"
    chosen = result["sets"][0]["members"]["loop3-bsmbi"]
    source = next(o for o in result["options"] if o["label"] == chosen)["materials"]["source_ssdna"]
    old = json.loads((prior_pool[1] / "summary.json").read_bytes())["options"][0]["material_roles"][
        "source_ssdna"
    ]
    assert source["material_id"] != old["material_id"]


def test_prior_material_selection_replays_after_relocation(prior_pool, tmp_path):
    path = reuse_request(tmp_path, prior_pool, method="bsai")
    packet = construction.execute_scaffold_comparison(path).write(tmp_path / "comparison")
    selected = construction.select_scaffold_comparison(
        packet, set_label="set-0001", baseline="loop3-bsai"
    ).write(tmp_path / "selected")
    moved = tmp_path / "moved"
    shutil.move(selected, moved)
    value = json.loads((moved / "set.json").read_bytes())
    assert value["reuse_prior_materials"]["roles"] == ["source_ssdna"]
    replay = construction.select_construction_set(moved / "set.json")
    summary = json.loads(replay.json_bytes)
    assert summary["prior_material_reference"]["required_roles"] == ["source_ssdna"]
    assert "source_ssdna" not in summary["prior_material_changes"]["loop3-bsai"]["changed_roles"]
    assert "Reuse from the verified prior preparation: source oligo" in replay.report_text


@pytest.mark.parametrize("conflict", ["chemistry", "fixed-source", "adapter-permission"])
def test_prior_reuse_does_not_override_existing_requirements(prior_pool, tmp_path, conflict):
    path = reuse_request(tmp_path, prior_pool)
    value = json.loads(path.read_bytes())
    source = value["discovery"]["product"]["materialization"]["source_preparation"]
    if conflict == "chemistry":
        source["source_ssdna"]["five_prime_end"] = "phosphate"
    elif conflict == "fixed-source":
        source["source_ssdna"] = {
            "mode": "fixed",
            "material": {
                "sequence_5prime": "ACGTACGT",
                "five_prime_end": "hydroxyl",
                "three_prime_end": "hydroxyl",
            },
        }
    else:
        value["reuse_prior_materials"]["roles"] = ["ligation_adapter"]
        value["discovery"]["preparation_changes"]["adapter_redesign"] = "allow"
    path.write_text(json.dumps(value))
    summary = json.loads(construction.prepare_scaffold_comparison(path).json_bytes)
    assert summary["status"] == "conflicting_requirements"
    assert summary["conflicts"]


def test_altered_prior_material_reference_is_rejected(prior_pool, tmp_path):
    path = reuse_request(tmp_path, prior_pool)
    value = json.loads(path.read_bytes())
    ref = value["reuse_prior_materials"]["reference"]
    copied = tmp_path / "changed"
    shutil.copytree(ref["bundle_path"], copied)
    artifact = next(p for p in copied.rglob("*.json") if p.name != "construction-bundle.json")
    artifact.write_bytes(artifact.read_bytes() + b" ")
    ref["bundle_path"] = str(copied)
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        construction.prepare_scaffold_comparison(path)
