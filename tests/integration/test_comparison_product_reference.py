"""A prior product is preserved by replaying its selected molecular authority."""

import json
import shutil

import pytest

from hop_design import construction
from tests.support.grouped_comparison import create_method_pool, grouped_brief


@pytest.fixture(scope="module")
def method_pool(tmp_path_factory):
    return create_method_pool(tmp_path_factory.mktemp("referenced-methods"))


def referenced_brief(tmp_path, discovery, pool):
    path = grouped_brief(tmp_path, discovery)
    request = json.loads(path.read_bytes())
    options = json.loads((pool / "summary.json").read_bytes())["options"]
    for group, loop in zip(request["groups"], (3, 4), strict=True):
        option = next(o for o in options if o["geometry"]["loop_nt"] == loop)
        group["product_reference"] = {
            **{k: str(pool / v) for k, v in option["selection"].items()},
            "stage": "endpoint",
        }
    path.write_text(json.dumps(request))
    return path


def test_group_product_locks_are_verified_embedded_and_portable(method_pool, tmp_path):
    discovery, pool = method_pool
    path = referenced_brief(tmp_path, discovery, pool)
    packet = construction.assess_scaffold_comparison(path, pool)
    summary = json.loads(packet.json_bytes)
    assert summary["status"] == "comparison_available"
    assert set(summary["product_references"]) == {"loop3", "loop4"}
    out = packet.write(tmp_path / "locked")
    saved = json.loads((out / "request.json").read_bytes())
    assert saved["groups"][0]["product_reference"]["bundle_path"].startswith("references/")
    moved = tmp_path / "moved"
    shutil.copytree(out, moved)
    selected = construction.select_scaffold_comparison(
        moved, set_label="set-0001", baseline="loop3-bsai"
    )
    files = dict(selected._files)
    assert any(k.startswith("comparison/references/") for k in files)
    assert "Matches prior selected product" in files["comparison/pages/comparison-1.svg"].decode()
    assert len(json.loads(selected.json_bytes)["members"]) == 4
    retrieved = selected.write(tmp_path / "retrieved")
    declaration = json.loads((retrieved / "comparison-selection.json").read_bytes())["request"]
    for group in declaration["groups"]:
        reference = group["product_reference"]
        assert (retrieved / reference["bundle_path"]).is_dir()
        assert (retrieved / reference["selection_path"]).is_file()
    draft = tmp_path / "reauthor"
    shutil.copytree(retrieved / "comparison/references", draft / "comparison/references")
    restored = draft / "request.json"
    restored.write_text(json.dumps(declaration))
    preview = construction.prepare_scaffold_comparison(restored)
    assert json.loads(preview.json_bytes)["status"] == "ready"
    portable = construction.prepare_scaffold_comparison(retrieved / "comparison/request.json")
    assert json.loads(portable.json_bytes)["status"] == "ready"


def test_different_locked_product_is_rejected_even_when_new_methods_agree(method_pool, tmp_path):
    discovery, pool = method_pool
    path = referenced_brief(tmp_path, discovery, pool)
    request = json.loads(path.read_bytes())
    request["groups"][0]["product_reference"] = request["groups"][1]["product_reference"]
    path.write_text(json.dumps(request))
    packet = construction.assess_scaffold_comparison(path, pool)
    summary = json.loads(packet.json_bytes)
    assert summary["sets"] == []
    assert summary["group_coverage"]["rejections"] == {"referenced_product_changed": 1}


def test_reference_stage_is_not_silently_reinterpreted(method_pool, tmp_path):
    discovery, pool = method_pool
    path = referenced_brief(tmp_path, discovery, pool)
    request = json.loads(path.read_bytes())
    request["groups"][0]["product_reference"]["stage"] = "hairpin"
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="stage"):
        construction.prepare_scaffold_comparison(path)


def test_modified_reference_fails_before_preview(method_pool, tmp_path):
    discovery, pool = method_pool
    path = referenced_brief(tmp_path, discovery, pool)
    request = json.loads(path.read_bytes())
    ref = request["groups"][0]["product_reference"]
    copied = tmp_path / "bad-authority"
    shutil.copytree(ref["bundle_path"], copied)
    artifact = next(p for p in copied.rglob("*.json") if p.name != "construction-bundle.json")
    artifact.write_bytes(artifact.read_bytes() + b" ")
    ref["bundle_path"] = str(copied)
    path.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        construction.prepare_scaffold_comparison(path)
