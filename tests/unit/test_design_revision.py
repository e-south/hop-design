"""Small permission revisions preserve the authored experimental intention."""

import json
from pathlib import Path

import pytest

from hop_design import construction
from tests.unit.test_construction_intent import STEM


def intent():
    return {"stem_arm": STEM, "product": "released_insert"}


def test_arm_revision_exposes_effective_diff_without_rewriting_intent():
    original = intent()
    preview = construction.preview_design_revision(
        original, {"parameters": [{"key": "foldback_arm_bp", "minimum": 3, "maximum": 5}]}
    )
    result = json.loads(preview.json_bytes)
    assert result["status"] == "ready"
    assert result["request"]["context"]["foldback"]["geometry"]["annealing_arm_lengths_bp"] == [
        3,
        4,
        5,
    ]
    assert result["request"]["stem_arm"] == STEM
    assert result["request"]["ends"] is None
    assert [change["path"] for change in result["changes"]] == [
        "foldback.geometry.annealing_arm_lengths_bp"
    ]
    assert original == intent()


def test_revision_cannot_silently_drop_a_hard_scaffold_requirement(tmp_path):
    original = {**intent(), "scaffold": {"loop_side_paired_bp": {"minimum": 6, "maximum": 6}}}
    preview = construction.preview_design_revision(
        original, {"parameters": [{"key": "foldback_arm_bp", "values": [3, 4, 5]}]}
    )
    result = json.loads(preview.json_bytes)
    assert result["status"] == "conflicting_requirements"
    assert result["conflicts"]
    assert result["request"]["scaffold"]["loop_side_paired_bp"] == {"minimum": 6, "maximum": 6}
    with pytest.raises(ValueError, match=r"conflict"):
        preview.execute(tmp_path / "must-not-exist", max_evaluations=1)
    assert not (tmp_path / "must-not-exist").exists()


def test_missing_method_characterization_is_a_dependency_not_an_invented_enzyme():
    preview = construction.preview_design_revision(intent(), {"methods": {"basal": ["Nb.BtsI"]}})
    result = json.loads(preview.json_bytes)
    assert result["status"] == "conflicting_requirements"
    assert "characteriz" in str(result["conflicts"]).lower()


def test_method_revision_binds_supplied_characterization_and_exposes_role_changes():
    root = Path(__file__).resolve().parents[2]
    example = json.loads((root / "examples/molecular-editing/request.json").read_text())
    enzyme = next(
        e
        for e in example["product"]["enzyme_catalog"]["enzymes"]
        if e["canonical_name"] == "Nb.BtsI"
    )
    preview = construction.preview_design_revision(
        intent(), {"methods": {"basal": ["Nb.BtsI"]}, "add_enzymes": [enzyme]}
    )
    result = json.loads(preview.json_bytes)
    assert result["status"] == "ready"
    role = next(
        r
        for r in result["request"]["context"]["basal"]["enzymes"]["role_restrictions"]
        if r["role"] == "basal_nick"
    )
    assert role["allowed_enzyme_ids"] == [enzyme["enzyme_id"]]
    assert {change["path"] for change in result["changes"]} >= {
        "enzyme_catalog.enzymes",
        "basal.enzymes.allowed_enzyme_ids",
        "basal.enzymes.role_restrictions",
    }


def test_relocated_preview_replays_and_cannot_be_resealed_with_a_changed_request(tmp_path):
    import shutil

    from hop_design.serialization import canonical_json_bytes, sha256_digest

    preview = construction.preview_design_revision(
        intent(), {"parameters": [{"key": "foldback_arm_bp", "values": [3, 4, 5]}]}
    )
    preview.write(tmp_path / "preview")
    shutil.copytree(tmp_path / "preview", tmp_path / "relocated")
    loaded = construction.load_design_revision(tmp_path / "relocated")
    assert loaded.json_bytes == preview.json_bytes
    path = tmp_path / "relocated/request.json"
    request = json.loads(path.read_bytes())
    request["stem_arm"] = "AAAA"
    path.write_bytes(canonical_json_bytes(request))
    manifest = tmp_path / "relocated/manifest.json"
    data = json.loads(manifest.read_bytes())
    data["artifacts"]["request.json"] = sha256_digest(path.read_bytes())
    manifest.write_bytes(canonical_json_bytes(data))
    with pytest.raises(ValueError, match=r"revision|disagree"):
        construction.load_design_revision(tmp_path / "relocated")


def test_overhead_conflict_is_located_before_search_and_requires_an_explicit_edit():
    from tests.integration.test_design_discovery import intent_document

    change = {"parameters": [{"key": "foldback_arm_bp", "values": [7]}]}
    blocked = json.loads(construction.preview_design_revision(intent_document(), change).json_bytes)
    assert blocked["status"] == "conflicting_requirements"
    assert any("max_retained_overhead_nt" in c["field"] for c in blocked["conflicts"])
    fixed = construction.preview_design_revision(
        intent_document(), {**change, "retained_limits_nt": {"foldback": 20}}
    )
    assert json.loads(fixed.json_bytes)["status"] == "ready"
